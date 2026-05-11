"""
E2E wiring tests: every DynamicReasoningEngine agent path through process_dynamic_query_with_plan.

- Default: monkeypatched agent methods (no external HTTP / LLM in agent layer).
- Validates dispatch, execution_results shape, and metadata.sources_used.

Run:
  pytest test_dynamic_reasoning_agents_e2e.py -v -m "not live_api"
Optional real HTTP (subset):
  LIVE_API_AGENTS_INTEGRATION=1 pytest test_dynamic_reasoning_agents_e2e.py -m live_api -v
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import List

import pytest

from graph.dynamic_reasoning_engine import LIVE_API_GRAPH_SOURCES, DynamicReasoningEngine
from models.schemas import (
    BioMCPResult,
    ClinicalTrialResult,
    EmaSearchResult,
    ChinaRegulatoryResult,
    LiveDataSearchResult,
    OpenFDAResult,
    PublicationResult,
    GraphNode,
    GraphPlan,
)
from agents.site_map_agent import (
    SiteMapRequest,
    SiteMapResponse,
    SiteCandidate,
    PopulationOverlay,
)
from agents.simulation_agent import SimulationResponse


def _live_integration() -> bool:
    return os.getenv("LIVE_API_AGENTS_INTEGRATION", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _stub_live_hit(source: str) -> LiveDataSearchResult:
    return LiveDataSearchResult(
        url=f"https://example.test/{source}",
        title=f"stub {source}",
        content="stub",
        source_domain=f"{source}.test",
        metadata={"e2e_stub": True},
    )


def _minimal_trial() -> ClinicalTrialResult:
    return ClinicalTrialResult(
        nct_id="NCT00000000",
        title="E2E stub trial",
        condition="stub",
        sponsor="stub",
        status="Recruiting",
        phase="Phase 2",
    )


def _apply_search_stub(source: str, engine: DynamicReasoningEngine, monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch the method the graph executor invokes for this search source."""
    if source == "claims_data":
        from agents.claims_data_agent import claims_data_agent as cda

        async def stub_rx(query: str, max_results: int = 50):
            return [{"stub_claims": True, "query": query}]

        monkeypatch.setattr(cda, "search_prescriptions", stub_rx)
        return

    if source == "payer_data":
        from agents.payer_data_agent import payer_data_agent as pda

        async def stub_prod(query: str, max_results: int = 50):
            return [{"stub_product": True, "query": query}]

        monkeypatch.setattr(pda, "search_products", stub_prod)
        return

    if source == "healthcare_analytics":
        from agents.healthcare_analytics_agent import healthcare_analytics_agent as haa

        async def stub_util(query: str, max_results: int = 50):
            return [{"stub_analytics": True, "query": query}]

        monkeypatch.setattr(haa, "analyze_drug_utilization", stub_util)
        return

    agent = engine.available_agents.get(source)
    assert agent is not None, f"no agent instance for {source}"

    if source in LIVE_API_GRAPH_SOURCES:

        async def stub_search(query: str, max_results: int = 50) -> List[LiveDataSearchResult]:
            return [_stub_live_hit(source)]

        monkeypatch.setattr(agent, "search", stub_search)
        return

    if source == "clinical_trials":

        async def stub_studies(query: str, max_results: int = 50):
            return [_minimal_trial()]

        monkeypatch.setattr(agent, "search_studies", stub_studies)
        return

    if source == "pubmed":

        async def stub_pub(query: str, max_results: int = 50):
            return [
                PublicationResult(
                    pmid="00000000",
                    title="E2E stub paper",
                    abstract="abstract",
                )
            ]

        monkeypatch.setattr(agent, "search_publications", stub_pub)
        return

    if source == "biomcp":

        async def stub_bio(query: str, max_results: int = 50):
            return [BioMCPResult(id="GO:0001", title="stub concept")]

        monkeypatch.setattr(agent, "search_data", stub_bio)
        return

    if source == "aact":

        async def stub_aact(
            query: str,
            max_results: int = 50,
            node_description=None,
            node_parameters=None,
        ):
            return [_minimal_trial()]

        monkeypatch.setattr(agent, "search_studies", stub_aact)
        return

    if source == "openfda":

        async def stub_fda(query: str, max_results: int = 50):
            return [
                OpenFDAResult(
                    brand_name=["StubBrand"],
                    generic_name=["stubinin"],
                    relevance_score=1.0,
                )
            ]

        monkeypatch.setattr(agent, "search_drugs", stub_fda)
        return

    if source == "google_search":

        async def stub_web(query: str, search_instructions: str = "", max_results: int = 50):
            from models.schemas import FiercePharmaResult

            return [
                FiercePharmaResult(
                    url="https://example.com/news",
                    title="stub news",
                    content="body",
                    publication_date="2024-01-01",
                    companies=[],
                    drugs=[],
                    topics=[],
                    relevance_score=0.5,
                    source_domain="example.com",
                    metadata={},
                )
            ]

        monkeypatch.setattr(agent, "search_web", stub_web)
        return

    if source == "trialtrove":

        async def stub_tt(query: str, max_results: int = 50):
            return [_minimal_trial()]

        monkeypatch.setattr(agent, "search_studies", stub_tt)
        return

    if source == "fda_labels":

        async def stub_lbl(query: str, max_results: int = 50):
            return [{"title": "Stub Label", "indications": "stub"}]

        monkeypatch.setattr(agent, "search_labels", stub_lbl)
        return

    if source == "site_trove":

        async def stub_sites(query: str, max_results: int = 50):
            from models.schemas import SiteResult

            return [
                SiteResult(
                    site_id="1",
                    site_name="Stub Site",
                    city="Boston",
                    state="MA",
                    country="US",
                )
            ]

        monkeypatch.setattr(agent, "search_sites", stub_sites)
        return

    if source == "goodrx":
        from models.schemas import FiercePharmaResult

        async def stub_grx(drug_names: List[str]):
            return [
                FiercePharmaResult(
                    url="https://goodrx.test/drug",
                    title=drug_names[0] if drug_names else "drug",
                    content="price stub",
                    publication_date=datetime.now().strftime("%Y-%m-%d"),
                    companies=[],
                    drugs=list(drug_names or ["stub"]),
                    topics=[],
                    relevance_score=0.5,
                    source_domain="goodrx.com",
                    metadata={},
                )
            ]

        monkeypatch.setattr(agent, "search_drugs", stub_grx)
        return

    if source == "ema_eu":

        async def stub_ema(query: str, max_results: int = 50):
            return [
                EmaSearchResult(
                    title="EMA stub",
                    sub_source="guidance_pages",
                    excerpt="stub",
                )
            ]

        monkeypatch.setattr(agent, "search", stub_ema)
        return

    if source == "china_regulatory":

        async def stub_cn(query: str, search_instructions: str = "", max_results: int = 50):
            return [
                ChinaRegulatoryResult(
                    url="https://cde.gov.cn/stub",
                    title="stub guidance",
                    content="stub text",
                    source_domain="cde.gov.cn",
                )
            ]

        monkeypatch.setattr(agent, "search_regulatory", stub_cn)
        return

    raise AssertionError(f"add stub mapping for search source: {source}")


def _payer_bundle_available() -> bool:
    """Payer / healthcare analytics agents import CSVs from backend/payer_data/."""
    return (Path(__file__).resolve().parent / "payer_data" / "Productbrand_Dim.csv").is_file()


# Search-backed agents (stubs; no network). Excludes payer/healthcare when CSV bundle absent — see below.
SEARCH_SOURCES_E2E = (
    "clinical_trials",
    "pubmed",
    "biomcp",
    "aact",
    "openfda",
    "google_search",
    "trialtrove",
    "fda_labels",
    "site_trove",
    "goodrx",
    "ema_eu",
    "china_regulatory",
    "nih_reporter",
    "npi_registry",
    "openalex",
    "crossref",
    "ror",
    "open_payments",
    "eu_ctis",
    "isrctn",
    "cms_open_data",
    "fda_datadashboard",
    "claims_data",
)

PAYER_BUNDLE_SEARCH_SOURCES = ("payer_data", "healthcare_analytics")


def _search_focus_for(source: str) -> str:
    """Steer branch selection for lazy commercial / analytics agents."""
    if source == "claims_data":
        return "prescription drug utilization metformin"
    if source == "payer_data":
        return "product aspirin brand therapeutic"
    if source == "healthcare_analytics":
        return "drug utilization prescription trends"
    return f"e2e smoke {source}"


@pytest.fixture(scope="module")
def reasoning_engine() -> DynamicReasoningEngine:
    return DynamicReasoningEngine()


async def _run_stubbed_search_source(
    reasoning_engine: DynamicReasoningEngine,
    source: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _apply_search_stub(source, reasoning_engine, monkeypatch)

    node_id = f"n_{source}"
    plan = GraphPlan(
        nodes=[
            GraphNode(
                id=node_id,
                type="search",
                description=f"e2e {source}",
                parameters={
                    "source": source,
                    "max_results": 3,
                    "search_focus": _search_focus_for(source),
                },
                dependencies=[],
            )
        ],
        edges=[],
        execution_order=[node_id],
        reasoning=f"e2e stub {source}",
    )

    resp = await reasoning_engine.process_dynamic_query_with_plan(
        f"integration query for {source}",
        plan,
    )

    assert source in (resp.metadata.sources_used or []), resp.metadata.sources_used
    rows = resp.results.get(node_id)
    assert rows is not None, f"missing results for {source}, keys={list(resp.results.keys())}"
    assert isinstance(rows, list)
    assert len(rows) >= 1, f"{source} returned empty list"


@pytest.mark.asyncio
@pytest.mark.engine_e2e
@pytest.mark.parametrize("source", SEARCH_SOURCES_E2E)
async def test_dynamic_reasoning_search_source_e2e_stubbed(
    reasoning_engine: DynamicReasoningEngine,
    source: str,
    monkeypatch: pytest.MonkeyPatch,
):
    """Each search source runs through the graph and writes execution_results."""
    await _run_stubbed_search_source(reasoning_engine, source, monkeypatch)


@pytest.mark.skipif(
    not _payer_bundle_available(),
    reason="backend/payer_data/*.csv not present (optional local bundle)",
)
@pytest.mark.asyncio
@pytest.mark.engine_e2e
@pytest.mark.parametrize("source", PAYER_BUNDLE_SEARCH_SOURCES)
async def test_dynamic_reasoning_search_source_e2e_stubbed_payer_bundle(
    reasoning_engine: DynamicReasoningEngine,
    source: str,
    monkeypatch: pytest.MonkeyPatch,
):
    """Payer + healthcare analytics require on-disk payer dimension CSVs to import."""
    await _run_stubbed_search_source(reasoning_engine, source, monkeypatch)


@pytest.mark.asyncio
@pytest.mark.engine_e2e
async def test_dynamic_reasoning_llm_search_source_empty(
    reasoning_engine: DynamicReasoningEngine,
):
    """llm is registered but has no search handler — should complete without error."""
    node_id = "n_llm"
    plan = GraphPlan(
        nodes=[
            GraphNode(
                id=node_id,
                type="search",
                description="llm as source",
                parameters={"source": "llm", "max_results": 2, "search_focus": "test"},
                dependencies=[],
            )
        ],
        edges=[],
        execution_order=[node_id],
        reasoning="e2e llm search no-op",
    )
    resp = await reasoning_engine.process_dynamic_query_with_plan("hello", plan)
    rows = resp.results.get(node_id)
    assert rows is not None
    assert rows == []


@pytest.mark.asyncio
@pytest.mark.engine_e2e
async def test_dynamic_reasoning_simulation_node_stubbed(
    reasoning_engine: DynamicReasoningEngine,
    monkeypatch: pytest.MonkeyPatch,
):
    from agents.simulation_agent import simulation_agent

    async def stub_run(req) -> SimulationResponse:
        return SimulationResponse(
            simulation_id="e2e-sim",
            query=req.query,
            status="completed",
            execution_mode="dynamic",
            results={"ok": True},
            timestamp=datetime.now().isoformat(),
            execution_time_seconds=0.01,
        )

    monkeypatch.setattr(simulation_agent, "run_simulation", stub_run)

    node_id = "sim1"
    plan = GraphPlan(
        nodes=[
            GraphNode(
                id=node_id,
                type="simulation",
                description="e2e simulation",
                parameters={},
                dependencies=[],
            )
        ],
        edges=[],
        execution_order=[node_id],
        reasoning="e2e simulation",
    )
    resp = await reasoning_engine.process_dynamic_query_with_plan("predict enrollment", plan)
    rows = resp.results.get(node_id)
    assert rows and isinstance(rows, list)
    payload = rows[0]
    assert isinstance(payload, dict)
    assert payload.get("simulation_id") == "e2e-sim"


@pytest.mark.asyncio
@pytest.mark.engine_e2e
async def test_dynamic_reasoning_site_map_node_stubbed(
    reasoning_engine: DynamicReasoningEngine,
    monkeypatch: pytest.MonkeyPatch,
):
    from agents.site_map_agent import site_map_agent

    async def stub_map(request: SiteMapRequest) -> SiteMapResponse:
        return SiteMapResponse(
            map_id="e2e-map",
            sites=[
                SiteCandidate(
                    site_id="1",
                    name="Site A",
                    address="1 St",
                    city="Boston",
                    state="MA",
                    zip_code="02101",
                    coordinates={"lat": 42.0, "lng": -71.0},
                )
            ],
            population_overlay=PopulationOverlay(),
            generated_at=datetime.now().isoformat(),
        )

    monkeypatch.setattr(site_map_agent, "generate_site_map", stub_map)

    node_id = "map1"
    plan = GraphPlan(
        nodes=[
            GraphNode(
                id=node_id,
                type="site_map",
                description="e2e map",
                parameters={"query": "trial sites US"},
                dependencies=[],
            )
        ],
        edges=[],
        execution_order=[node_id],
        reasoning="e2e site map",
    )
    resp = await reasoning_engine.process_dynamic_query_with_plan("site map oncology", plan)
    rows = resp.results.get(node_id)
    assert rows and isinstance(rows, list)
    inner = rows[0]
    assert isinstance(inner, dict)
    assert inner.get("map_id") == "e2e-map"


# --- Optional: same entrypoint, real HTTP for a few stable live APIs ---


@pytest.mark.live_api
@pytest.mark.engine_e2e
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "source,query",
    [
        ("nih_reporter", "cancer"),
        ("npi_registry", "Mayo Clinic"),
        ("open_payments", "general"),
        ("eu_ctis", "diabetes"),
        ("isrctn", "stroke"),
        ("cms_open_data", "hospital"),
    ],
)
async def test_dynamic_reasoning_live_search_sample(
    reasoning_engine: DynamicReasoningEngine,
    source: str,
    query: str,
):
    if not _live_integration():
        pytest.skip("set LIVE_API_AGENTS_INTEGRATION=1")

    node_id = f"live_{source}"
    plan = GraphPlan(
        nodes=[
            GraphNode(
                id=node_id,
                type="search",
                description=f"live {source}",
                parameters={"source": source, "max_results": 2, "search_focus": query},
                dependencies=[],
            )
        ],
        edges=[],
        execution_order=[node_id],
        reasoning="live e2e",
    )
    resp = await reasoning_engine.process_dynamic_query_with_plan(query, plan)
    rows = resp.results.get(node_id) or []
    if not rows:
        pytest.skip(f"{source}: empty live response (rate limit or API change)")
    assert rows[0].get("title") or rows[0].get("url")
