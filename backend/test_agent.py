"""Standalone end-to-end test for the CI agent graph (BUILD_GUIDE Phase 3).

Runs the compiled LangGraph pipeline for **Target: Linear** vs
**Competitor: Jira** and prints the validated battlecard JSON.

Run::

    python test_agent.py

Requires ``GEMINI_API_KEY`` (or ``LLM_FAST_MODEL``/``LLM_HEAVY_MODEL``
pointing at another provider with its key) and ``TAVILY_API_KEY``. Values
are read from the environment or the repo-root ``.env`` file.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent

sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(REPO_ROOT / ".env")

REQUIRED_KEYS = ("GEMINI_API_KEY", "TAVILY_API_KEY")


def validate_environment() -> None:
    """Fail fast with a friendly message when keys are not configured."""
    for key in REQUIRED_KEYS:
        value = os.getenv(key, "").strip()
        if not value or "replace_with" in value:
            print(
                f"[config] {key} is not configured. Set it in "
                f"{REPO_ROOT / '.env'} or your environment before running.",
                file=sys.stderr,
            )
            sys.exit(2)


def initial_state() -> dict:
    """Seed the graph with SPEC §5-compliant default channels."""
    return {
        "target": "Linear",
        "competitor": "Jira",
        "sub_queries": [],
        "scraped_content": [],
        "verified_corpus": "",
        "validation_flags": {},
        "retries": 0,
        "is_valid": False,
        "final_output": {},
    }


async def main() -> None:
    from app.agents.ci_graph import build_ci_graph

    validate_environment()
    print("== CI Agent: Linear vs Jira ==")
    print("Compiling graph ...")
    graph = build_ci_graph()

    print("Running plan -> retrieve -> verify -> synthesize ...\n")
    result = await graph.ainvoke(initial_state())

    print(
        "Summary:\n"
        f"  valid evidence    : {result.get('is_valid')}\n"
        f"  verification loops: {result.get('retries')}\n"
        f"  sources scraped   : {len(result.get('scraped_content') or [])}\n"
    )
    print("Battlecard JSON:")
    print(json.dumps(result.get("final_output"), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAborted by user.", file=sys.stderr)
        sys.exit(130)