"""
Execute LIVE_API_GRAPH_SOURCES through DynamicReasoningEngine.process_dynamic_query_with_plan.

- Default: each source is stubbed with a fake async search (validates graph wiring + dispatch).
- Optional: LIVE_API_AGENTS_INTEGRATION=1 and -m live_api runs real HTTP for selected sources.
"""
from __future__ import annotations

import os
from typing import List

import pytest

from graph.dynamic_reasoning_engine import LIVE_API_GRAPH_SOURCES, DynamicReasoningEngine
from models.schemas import GraphNode, GraphPlan, LiveDataSearchResult


def _live_integration() -> bool:
    return os.getenv("LIVE_API_AGENTS_INTEGRATION", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _stub_hits(source: str) -> List[LiveDataSearchResult]:
    return [
        LiveDataSearchResult(
            url="https://example.com/record",
            title=f"Stub hit for {source}",
            content="stub content",
            source_domain=f"stub.{source}",
            metadata={"stub": True, "source": source},
        )
    ]


@pytest.fixture(scope="module")
def reasoning_engine() -> DynamicReasoningEngine:
    """One engine per module — first import is slow (claims CSV, agents)."""
    return DynamicReasoningEngine()


@pytest.mark.asyncio
@pytest.mark.parametrize("source", sorted(LIVE_API_GRAPH_SOURCES))
async def test_engine_custom_plan_dispatches_live_api_source(
    reasoning_engine: DynamicReasoningEngine, source: str, monkeypatch: pytest.MonkeyPatch
):
    """Single-node search plan hits the correct agent.search via the graph executor."""
    agent = reasoning_engine.available_agents.get(source)
    assert agent is not None, f"missing agent for {source}"

    async def stub_search(query: str, max_results: int = 50):
        return _stub_hits(source)

    monkeypatch.setattr(agent, "search", stub_search)

    node_id = f"search_{source}"
    plan = GraphPlan(
        nodes=[
            GraphNode(
                id=node_id,
                type="search",
                description=f"Test {source}",
                parameters={"source": source, "max_results": 3},
                dependencies=[],
            )
        ],
        edges=[],
        execution_order=[node_id],
        reasoning=f"unit test wiring for {source}",
    )

    resp = await reasoning_engine.process_dynamic_query_with_plan(
        f"test query for {source} integration",
        plan,
    )

    assert source in (resp.metadata.sources_used or []), resp.metadata.sources_used
    rows = resp.results.get(node_id)
    assert rows is not None, f"no execution_results[{node_id}], keys={list(resp.results.keys())}"
    assert len(rows) >= 1
    assert rows[0].get("title") or rows[0].get("url")


@pytest.mark.asyncio
async def test_engine_multi_source_plan_sequential(
    reasoning_engine: DynamicReasoningEngine, monkeypatch: pytest.MonkeyPatch
):
    """Two live-api search nodes in sequence both populate execution_results."""
    called: list[str] = []

    def make_stub(src: str):
        async def stub(query: str, max_results: int = 50):
            called.append(src)
            return _stub_hits(src)

        return stub

    for s in ("openalex", "crossref"):
        monkeypatch.setattr(reasoning_engine.available_agents[s], "search", make_stub(s))

    plan = GraphPlan(
        nodes=[
            GraphNode(
                id="s1",
                type="search",
                description="OpenAlex",
                parameters={"source": "openalex", "max_results": 2},
                dependencies=[],
            ),
            GraphNode(
                id="s2",
                type="search",
                description="Crossref",
                parameters={"source": "crossref", "max_results": 2},
                dependencies=[],
            ),
        ],
        edges=[],
        execution_order=["s1", "s2"],
        reasoning="sequential live API test",
    )

    resp = await reasoning_engine.process_dynamic_query_with_plan("diabetes publications metadata", plan)
    assert called == ["openalex", "crossref"]
    assert len(resp.results.get("s1", [])) >= 1
    assert len(resp.results.get("s2", [])) >= 1


# --- Optional real network (same entrypoint as production custom plan) ---


@pytest.mark.live_api
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source,query",
    [
        ("openalex", "machine learning drug discovery"),
        ("crossref", "10.1038/nature"),
        ("ror", "University of Oxford"),
    ],
)
async def test_engine_real_http_sample_sources(
    reasoning_engine: DynamicReasoningEngine, source: str, query: str
):
    if not _live_integration():
        pytest.skip("set LIVE_API_AGENTS_INTEGRATION=1")

    node_id = f"live_{source}"
    plan = GraphPlan(
        nodes=[
            GraphNode(
                id=node_id,
                type="search",
                description=f"Live {source}",
                parameters={"source": source, "max_results": 2},
                dependencies=[],
            )
        ],
        edges=[],
        execution_order=[node_id],
        reasoning="live API smoke via DynamicReasoningEngine",
    )

    resp = await reasoning_engine.process_dynamic_query_with_plan(query, plan)
    rows = resp.results.get(node_id) or []
    if not rows:
        pytest.skip(f"{source}: no results from live API")
    assert rows[0].get("title") or rows[0].get("url")
