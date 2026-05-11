"""Unit tests for deep research helpers (no live agents)."""
import uuid
from unittest.mock import AsyncMock

import pytest

from graph.dynamic_reasoning_engine import DynamicReasoningEngine
from graph.deep_research import (
    merge_replan_into_plan,
    node_result_ok_for_skip,
    dedupe_citation_dicts,
    format_research_spec_for_planner,
)
from models.schemas import GraphNode, GraphPlan, PublicationResult


def test_node_result_ok_for_skip():
    assert node_result_ok_for_skip([{"nct_id": "NCT1"}]) is True
    assert node_result_ok_for_skip([]) is False
    assert node_result_ok_for_skip({"error": "x"}) is False
    assert node_result_ok_for_skip({"answer": "ok"}) is True


def test_merge_replan_inserts_before_synthesize():
    base = GraphPlan(
        nodes=[
            GraphNode(id="s1", type="search", description="a", parameters={"source": "pubmed"}, dependencies=[]),
            GraphNode(id="syn", type="synthesize", description="s", parameters={}, dependencies=["s1"]),
        ],
        edges=[{"from": "s1", "to": "syn"}],
        execution_order=["s1", "syn"],
        reasoning="t",
    )
    new_nodes = [
        GraphNode(
            id="replan_r1_x",
            type="search",
            description="fill gap",
            parameters={"source": "google_search"},
            dependencies=["s1"],
        )
    ]
    merged = merge_replan_into_plan(base, new_nodes, [{"from": "s1", "to": "replan_r1_x"}])
    assert merged.execution_order == ["s1", "replan_r1_x", "syn"]
    assert any(n.id == "replan_r1_x" for n in merged.nodes)


def test_dedupe_citations():
    c = dedupe_citation_dicts(
        [
            {"text": "a", "url": "https://x"},
            {"text": "b", "url": "https://x"},
            {"text": "c", "url": "https://y"},
        ]
    )
    assert len(c) == 2


def test_format_research_spec_contains_section():
    spec = {
        "brief": "b",
        "assumptions": ["a1"],
        "must_have_facts": ["m1"],
        "outline": [{"section_id": "foo", "title": "Foo", "sub_questions": ["q1"]}],
    }
    txt = format_research_spec_for_planner(spec)
    assert "[foo]" in txt
    assert "q1" in txt


@pytest.fixture
def reasoning_engine() -> DynamicReasoningEngine:
    return DynamicReasoningEngine()


@pytest.mark.asyncio
@pytest.mark.engine_e2e
async def test_process_dynamic_query_deep_research_smoke_stubbed(
    reasoning_engine: DynamicReasoningEngine,
    monkeypatch: pytest.MonkeyPatch,
):
    """Full deep-research path: brief → plan → execute → verify, without live LLM in agents."""
    events: list[str] = []

    async def progress_cb(data: dict):
        t = data.get("type")
        if t in (
            "research_brief_ready",
            "research_outline_ready",
            "verifier_result",
            "replan_started",
            "deep_research_phase",
            "subruns_merged",
        ):
            events.append(str(t))

    async def brief(_q: str):
        return {
            "brief": "scope",
            "assumptions": [],
            "must_have_facts": [],
            "outline": [{"section_id": "sec1", "title": "T", "sub_questions": ["q1"]}],
        }

    async def verdict(*_a, **_k):
        return {
            "passed": True,
            "section_status": [],
            "gaps": [],
            "contradictions": [],
            "confidence": "high",
        }

    plan = GraphPlan(
        nodes=[
            GraphNode(
                id="p1",
                type="search",
                description="pubmed e2e",
                parameters={"source": "pubmed", "max_results": 2, "search_focus": "diabetes trial"},
                dependencies=[],
            ),
            GraphNode(
                id="syn1",
                type="synthesize",
                description="final",
                parameters={"synthesis_type": "comprehensive_summary"},
                dependencies=["p1"],
            ),
        ],
        edges=[{"from": "p1", "to": "syn1"}],
        execution_order=["p1", "syn1"],
        reasoning="deep smoke",
    )

    async def fake_assess(*_a, **_k):
        return plan

    pub = reasoning_engine.available_agents["pubmed"]

    async def stub_pub(query: str, max_results: int = 50):
        return [
            PublicationResult(
                pmid="12345",
                title="Stub paper",
                abstract="abstract",
                authors=["A"],
                journal="J",
                publication_date="2024-01-01",
            )
        ]

    monkeypatch.setattr("graph.dynamic_reasoning_engine.build_research_brief_and_outline", brief)
    monkeypatch.setattr("graph.dynamic_reasoning_engine.verify_research_coverage", verdict)
    monkeypatch.setattr(reasoning_engine, "assess_query_and_plan_graph", fake_assess)
    monkeypatch.setattr(pub, "search_publications", stub_pub)
    monkeypatch.setattr(reasoning_engine, "_synthesis_with_fallback", AsyncMock(return_value="Synthetic answer for test."))

    q = f"deep research smoke {uuid.uuid4()}"
    resp = await reasoning_engine.process_dynamic_query(
        q,
        include_graph_plan=True,
        progress_callback=progress_cb,
        deep_research=True,
    )

    assert resp.metadata.deep_research_run_id
    assert resp.metadata.deep_research_replan_rounds == 0
    assert resp.metadata.deep_research_verifier_passed is True
    assert "p1" in resp.results
    assert "syn1" in resp.results
    assert "research_brief_ready" in events
    assert "research_outline_ready" in events
    assert "verifier_result" in events


@pytest.mark.asyncio
async def test_llm_judge_smoke_skipped_without_keys(monkeypatch):
    """Does not call network if LLM is stubbed."""
    from graph import deep_research_eval

    async def fake_generate(*args, **kwargs):
        return '{"score": 4, "passes": true, "rationale": "ok"}'

    monkeypatch.setattr(deep_research_eval.llm_agent, "generate_structured_response", fake_generate)
    out = await deep_research_eval.llm_judge_completeness("q", [], "answer")
    assert out.get("passes") is True
