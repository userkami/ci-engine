"""Compiled LangGraph workflow for the autonomous CI research pipeline.

State, nodes and transitions follow SPEC.md §5:

    plan -> retrieve -> verify -+-> retrieve   (loop while invalid & retries < 2)
                                 +-> synthesize -> (end)

The graph is *compiled* (``.compile()``) so the same instance can be run
with ``invoke``/``ainvoke`` and, later, checkpointed for the durable
execution layer (Phase 4: Celery worker + SSE progress).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    planner_node,
    retriever_node,
    synthesis_node,
    verification_node,
)


def _merge_lists(left: list | None, right: list | None) -> list:
    """Reducer that concatenates updates without failing on ``None``.

    Used instead of ``operator.add`` so the graph tolerates callers who
    seed the state without pre-initialising the accumulated channels.
    """
    return list(left or []) + list(right or [])


#: Shared state of the CI graph. ``scraped_content`` uses a merge reducer
#: so retriever iterations accumulate documents instead of overwriting.
class CIState(TypedDict, total=False):
    target: str
    competitor: str
    sub_queries: list[str]
    scraped_content: Annotated[list[dict[str, str]], _merge_lists]
    verified_corpus: str
    validation_flags: dict[str, bool]
    retries: int
    is_valid: bool
    final_output: dict[str, Any]


def _route_after_verification(state: CIState) -> Literal["retriever", "synthesizer"]:
    """Conditional routing: retry the retriever or move to synthesis.

    Returns ``"synthesizer"`` when the corpus passed validation or the
    retry budget is exhausted (SPEC §5, max 2 retries); otherwise loops
    back into ``"retriever"`` with the refined gap queries.
    """
    if bool(state.get("is_valid")) or int(state.get("retries") or 0) >= 2:
        return "synthesizer"
    return "retriever"


def build_ci_graph():
    """Assemble and compile the CI research graph.

    Returns a compiled graph invokable with ``await graph.ainvoke(state)``.
    """
    builder = StateGraph(CIState)
    builder.add_node("planner", planner_node)
    builder.add_node("retriever", retriever_node)
    builder.add_node("verifier", verification_node)
    builder.add_node("synthesizer", synthesis_node)

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "retriever")
    builder.add_edge("retriever", "verifier")
    builder.add_conditional_edges("verifier", _route_after_verification)
    builder.add_edge("synthesizer", END)

    return builder.compile()