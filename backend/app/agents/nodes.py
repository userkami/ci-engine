"""LangGraph node implementations for the competitive intelligence pipeline.

Each node is an ``async`` function that receives the current graph state
(a :class:`~app.agents.ci_graph.CIState` dict) and returns a partial
state-update ``dict``. Nodes are wired and compiled in
:mod:`app.agents.ci_graph`.

Pipeline (SPEC.md §5):
    planner -> retriever -> verifier -+-> retriever (loop, max 2 retries)
                                       +-> synthesizer -> (end)
"""

from __future__ import annotations

import asyncio
import contextvars
import json
import logging
import os
import re
from typing import Any, Awaitable, Callable, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.schemas import BattlecardOutput
from app.core.llm import get_chat_model

logger = logging.getLogger(__name__)

#: Optional async hook invoked as each graph node starts. The Celery task
#: registers a publisher here (via ``set_progress_hook``) so progress can be
#: streamed over Redis Pub/Sub without coupling the agent nodes to Redis.
ProgressHook = Callable[[str, str], Awaitable[None]]
_progress_hook_var: contextvars.ContextVar[Optional[ProgressHook]] = (
    contextvars.ContextVar("ci_progress_hook", default=None)
)


def set_progress_hook(hook: Optional[ProgressHook]) -> contextvars.Token:
    """Register an async ``(step, message)`` callback for this context."""
    return _progress_hook_var.set(hook)


def reset_progress_hook(token: contextvars.Token) -> None:
    """Restore the previous hook state (see :func:`set_progress_hook`)."""
    _progress_hook_var.reset(token)


async def _emit_progress(step: str, message: str) -> None:
    """Best-effort progress notification; never breaks the graph."""
    hook = _progress_hook_var.get()
    if hook is None:
        return
    try:
        await hook(step, message)
    except Exception:
        logger.exception("progress hook failed for step %r", step)

# --------------------------------------------------------------------------- #
# Tunables (SPEC.md §5)
# --------------------------------------------------------------------------- #
MAX_CONTENT_CHARS = 8000          # per-document cap for scraped pages
MAX_CORPUS_CHARS = 45000          # total verified corpus handed to synthesis
MAX_SEARCH_RESULTS = 2            # Tavily results per sub-query
MAX_RETRIES = 2                   # verification loop-back allowance
SCRAPE_CONCURRENCY = 4            # parallel Firecrawl fetches

#: Deterministic fallback sub-queries so the planner never stalls.
PLANNER_TEMPLATES: List[str] = [
    "{competitor} pricing plans cost per user comparison {target} 2026",
    "{competitor} pricing hidden fees seat minimums annual billing",
    "{competitor} reviews complaints G2 Capterra pain points",
    '"{competitor}" reddit why customers left switched to {target}',
    "{competitor} changelog product updates 2025 2026 price increase",
]

PRICE_PATTERN = re.compile(
    r"(?i)(?:\$\s?[0-9]|€\s?[0-9]|£\s?[0-9]|usd\s?[0-9]|"
    r"per\s+(?:user|seat|month|year|project)|/mo|/month|"
    r"annual(?:ly)?\s+billing|contact\s+sales)"
)

QUOTED_PATTERN = re.compile(r'"([^"\n]{20,400})"')

PLATFORM_HINTS = ("g2", "capterra", "reddit", "trustpilot", "producthunt")
COMPLAINT_WORDS = (
    "bug", "glitch", "slow", "laggy", "expensive", "price", "support",
    "cancel", "migrat", "switch", "quit", "abandon", "frustrat",
    "downtime", "error",
)

_SYSTEM_PROMPT = """You are a senior competitive intelligence analyst for a B2B SaaS sales team.
You produce citation-backed battlecards from a research corpus.

RULES:
1. EVERY pricing tier and churn driver MUST cite a real source_url present in the corpus.
2. exact_quote MUST be copied verbatim from the corpus review text.
3. If evidence for a section is missing, return an empty list for that section and
   state the gap clearly in the executive summary. NEVER fabricate prices, quotes,
   features, or URLs.
4. The output must faithfully fill the provided JSON schema."""


# --------------------------------------------------------------------------- #
# Small shared utilities
# --------------------------------------------------------------------------- #
def _configured(name: str) -> bool:
    """True when an env var is set and not left as a template placeholder."""
    value = os.getenv(name, "").strip()
    return bool(value) and "replace_with" not in value


def _extract_json(text: str) -> Any:
    """Parse the first JSON value embedded in ``text`` (tolerates fences)."""
    text = re.sub(r"```(?:json)?", "", text).strip()
    start = min(
        (i for i in (text.find("["), text.find("{")) if i >= 0),
        default=-1,
    )
    if start < 0:
        raise ValueError("no JSON object/array found in model output")
    value, _ = json.JSONDecoder().raw_decode(text[start:])
    return value


# --------------------------------------------------------------------------- #
# Planner
# --------------------------------------------------------------------------- #
async def planner_node(state: dict) -> dict:
    """Generate targeted search sub-queries (pricing, reviews, changelogs).

    Uses the fast model; falls back to deterministic templates when the
    model call fails or returns unusable output.
    """
    target = state.get("target", "")
    competitor = state.get("competitor", "")
    await _emit_progress(
        "planning", f"Planning targeted research queries for {competitor}"
    )
    return {"sub_queries": await _generate_sub_queries(target, competitor)}


async def _generate_sub_queries(target: str, competitor: str) -> List[str]:
    fallback = [
        t.format(target=target, competitor=competitor)
        for t in PLANNER_TEMPLATES
    ]
    try:
        model = await get_chat_model("fast")
        messages = [
            SystemMessage(
                content=(
                    "You are a competitive research planner. Output ONLY a JSON "
                    "array of 4-6 concise, search-engine-ready sub-queries covering "
                    "competitor pricing, customer complaints (G2/Capterra/Reddit), "
                    "and product changelogs."
                )
            ),
            HumanMessage(
                content=(
                    f"Target company: {target}\n"
                    f"Competitor: {competitor}\n"
                    f"Return the JSON array of query strings now."
                )
            ),
        ]
        response = await model.ainvoke(messages)  # type: ignore[union-attr]
        queries = _extract_json(str(response.content))
        if isinstance(queries, list):
            cleaned = [str(q).strip() for q in queries if str(q).strip()]
            if cleaned:
                return cleaned[:6]
    except Exception:
        pass  # fall through to deterministic templates
    return fallback


# --------------------------------------------------------------------------- #
# Retriever
# --------------------------------------------------------------------------- #
async def retriever_node(state: dict) -> dict:
    """Search with Tavily and scrape promising links with Firecrawl.

    Falls back gracefully: failed search results and failed scrapes are
    skipped, never fatal. Accumulated content is returned under
    ``scraped_content`` so the verify->retrieve loop can append evidence.
    """
    competitor = state.get("competitor", "")
    queries: List[str] = list(state.get("sub_queries") or [])
    await _emit_progress(
        "retrieving", f"Searching and scraping sources for {competitor}"
    )
    documents = list(state.get("scraped_content") or [])
    seen_urls = {doc.get("url", "") for doc in documents}

    sem = asyncio.Semaphore(SCRAPE_CONCURRENCY)

    async def fetch(item: dict) -> dict[str, str] | None:
        url = (item.get("url") or "").strip()
        if not url or url in seen_urls:
            return None
        async with sem:
            content = await _extract_content_for(item)
        if not content:
            return None
        return {
            "url": url,
            "title": (item.get("title") or "")[:300],
            "content": content,
        }

    for query in queries:
        results = await _tavily_search(query)
        if not results:
            continue
        for fetched in await asyncio.gather(*(fetch(r) for r in results)):
            if fetched and fetched["url"] not in seen_urls:
                documents.append(fetched)
                seen_urls.add(fetched["url"])

    # Best-effort direct scrape of the competitor /pricing page (SPEC §5).
    pricing_url = await _pricing_url_for(competitor)
    if pricing_url and pricing_url not in seen_urls:
        markdown = await scrape_url(pricing_url)
        if markdown:
            documents.append(
                {
                    "url": pricing_url,
                    "title": f"{competitor} pricing",
                    "content": markdown,
                }
            )

    return {"scraped_content": documents}


async def _tavily_search(query: str) -> List[dict]:
    """Run a Tavily search; return the raw results list (empty on failure)."""
    if not _configured("TAVILY_API_KEY"):
        raise RuntimeError(
            "TAVILY_API_KEY is not configured. Set it in the .env file "
            "or your environment before running the agent."
        )
    try:
        from tavily import TavilyClient  # imported lazily (optional dep)

        client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

        def _search(depth: str) -> dict:
            return client.search(
                query=query,
                max_results=MAX_SEARCH_RESULTS,
                search_depth=depth,
                include_raw_content=True,
                include_answer=False,
            )

        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(
                None, lambda: _search("advanced")
            )
        except Exception:
            response = await loop.run_in_executor(
                None, lambda: _search("basic")
            )
        return list(response.get("results") or [])
    except Exception:
        return []


async def _extract_content_for(item: dict) -> str:
    """Best effort: Firecrawl markdown, then Tavily raw/snippet fallback."""
    url = (item.get("url") or "").strip()
    if _configured("FIRECRAWL_API_KEY") and url:
        scraped = await scrape_url(url)
        if scraped:
            return scraped
    raw = item.get("raw_content") or item.get("content") or ""
    return str(raw)[:MAX_CONTENT_CHARS]


async def _pricing_url_for(competitor: str) -> str | None:
    """Guess ``https://<slug>.com/pricing`` (best effort; None when unsure)."""
    slug = re.sub(r"[^a-z0-9]+", "", competitor.lower())
    if not slug or len(slug) < 3:
        return None
    return f"https://{slug}.com/pricing"


async def scrape_url(url: str) -> str | None:
    """Firecrawl markdown extraction (v2 ``Firecrawl`` with v1 fallback)."""
    if not _configured("FIRECRAWL_API_KEY"):
        return None
    api_key = os.environ["FIRECRAWL_API_KEY"]
    loop = asyncio.get_running_loop()

    def _read_markdown(doc: Any) -> str | None:
        if isinstance(doc, dict):
            return doc.get("markdown")
        return getattr(doc, "markdown", None)

    try:  # firecrawl-py v2
        from firecrawl import AsyncFirecrawl

        fc = AsyncFirecrawl(api_key=api_key)
        doc = await fc.scrape(url, formats=["markdown"])
        text = _read_markdown(doc)
        if text:
            return str(text)[:MAX_CONTENT_CHARS]
    except Exception:
        pass

    try:  # firecrawl-py v1 (legacy)
        from firecrawl import FirecrawlApp

        app = FirecrawlApp(api_key=api_key)
        doc = await loop.run_in_executor(
            None,
            lambda: app.scrape_url(url, formats=["markdown"]),
        )
        text = _read_markdown(doc)
        if text:
            return str(text)[:MAX_CONTENT_CHARS]
    except Exception:
        pass

    return None


# --------------------------------------------------------------------------- #
# Verifier
# --------------------------------------------------------------------------- #
async def verification_node(state: dict) -> dict:
    """Assess whether the corpus holds real pricing + review evidence.

    Sets ``is_valid`` and, when evidence is missing and retries remain,
    appends targeted gap queries and increments ``retries`` so the router
    can loop back into the retriever (max ``MAX_RETRIES`` loops).
    """
    docs = list(state.get("scraped_content") or [])
    corpus = "\n\n".join(
        f"URL: {doc.get('url', '')}\n{doc.get('content', '')}" for doc in docs
    )[:MAX_CORPUS_CHARS]

    flags = _analyze_corpus(corpus)
    is_valid = bool(flags["pricing_found"] and flags["quotes_found"])
    competitor = state.get("competitor", "")
    await _emit_progress(
        "verifying", "Verifying pricing and review evidence in the corpus"
    )

    gap_queries: List[str] = []
    if not flags["pricing_found"]:
        gap_queries.append(
            f"{competitor} pricing plans cost per user per month annual billing"
        )
    if not flags["quotes_found"]:
        gap_queries.append(
            f'"{competitor}" reviews complaints g2 capterra reddit why switched'
        )

    update: dict[str, Any] = {
        "verified_corpus": corpus,
        "validation_flags": flags,
        "is_valid": is_valid,
    }
    if gap_queries and int(state.get("retries") or 0) < MAX_RETRIES:
        update["sub_queries"] = gap_queries
        update["retries"] = int(state.get("retries") or 0) + 1
    return update


def _analyze_corpus(corpus: str) -> dict[str, bool]:
    """Heuristic evidence scan: does the corpus actually have substance?"""
    lowered = corpus.lower()
    pricing_found = bool(PRICE_PATTERN.search(corpus))
    quoted = QUOTED_PATTERN.findall(corpus)
    platform_hits = [w for w in PLATFORM_HINTS if w in lowered]
    complaint_hits = [w for w in COMPLAINT_WORDS if w in lowered]
    quotes_found = bool(quoted) or (
        bool(platform_hits) and bool(complaint_hits)
    )
    return {
        "pricing_found": pricing_found,
        "quotes_found": quotes_found,
        "quoted_count": len(quoted),
        "platforms": platform_hits,
    }


# --------------------------------------------------------------------------- #
# Synthesizer
# --------------------------------------------------------------------------- #
async def synthesis_node(state: dict) -> dict:
    """Run the heavy model with structured output to produce the battlecard."""
    target = state.get("target", "")
    competitor = state.get("competitor", "")
    corpus = state.get("verified_corpus") or _fallback_corpus(state)
    flags = state.get("validation_flags") or {}
    await _emit_progress(
        "synthesizing",
        "Synthesizing the battlecard report with the heavy model",
    )

    messages = _build_synthesis_prompt(target, competitor, corpus, flags)
    model = await get_chat_model("heavy")
    structured = model.with_structured_output(BattlecardOutput)
    response = await structured.ainvoke(messages)  # type: ignore[union-attr]
    battlecard = _coerce_structured_output(response, BattlecardOutput)
    return {"final_output": battlecard.model_dump(mode="json")}


def _build_synthesis_prompt(
    target: str,
    competitor: str,
    corpus: str,
    flags: dict[str, bool],
) -> list:
    evidence_note = (
        f"pricing evidence: {'FOUND' if flags.get('pricing_found') else 'MISSING'}; "
        f"review evidence: {'FOUND' if flags.get('quotes_found') else 'MISSING'}"
    )
    human = (
        f"Research target: {target}\n"
        f"Competitor: {competitor}\n"
        f"Evidence status -> {evidence_note}\n\n"
        f"Research corpus:\n{corpus[:MAX_CORPUS_CHARS]}\n\n"
        f"Produce the complete battlecard JSON matching the output schema."
    )
    return [SystemMessage(content=_SYSTEM_PROMPT), HumanMessage(content=human)]


def _fallback_corpus(state: dict) -> str:
    return "\n\n".join(
        f"URL: {doc.get('url', '')}\n{doc.get('content', '')}"
        for doc in state.get("scraped_content") or []
    )[:MAX_CORPUS_CHARS]


def _coerce_structured_output(
    response: Any, schema: type[BattlecardOutput]
) -> BattlecardOutput:
    """Tolerantly extract a validated schema from a provider response.

    Handles the different shapes LangChain providers return for
    ``with_structured_output`` (dict, JSON string, ``.parsed``, or the
    newer ``content_blocks`` payloads).
    """
    if isinstance(response, schema):
        return response

    content = getattr(response, "content", None)
    if isinstance(content, schema):
        return content
    if isinstance(content, dict):
        return schema.model_validate(content)
    if isinstance(content, str):
        try:
            return schema.model_validate(_extract_json(content))
        except Exception:
            pass  # try the response-level attributes below

    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, schema):
        return parsed
    if isinstance(parsed, dict):
        return schema.model_validate(parsed)

    for block in getattr(response, "content_blocks", None) or []:
        data = (
            getattr(block, "structured_output", None)
            or getattr(block, "data", None)
        )
        if isinstance(data, schema):
            return data
        if isinstance(data, dict):
            return schema.model_validate(data)

    raise ValueError(
        f"could not parse structured output from response of type "
        f"{type(response).__name__}"
    )