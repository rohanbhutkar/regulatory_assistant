"""
Tests for OpenFDAAgent query planning and Drugs@FDA search structuring.

Run from backend:
  pytest test_openfda_agent_structuring.py -q
  OPENFDA_INTEGRATION=1 pytest test_openfda_agent_structuring.py -q -m integration
"""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, patch

import pytest

from agents.openfda_agent import OpenFDAAgent

live_openfda = pytest.mark.skipif(
    os.getenv("OPENFDA_INTEGRATION", "").lower() not in ("1", "true", "yes"),
    reason="Set OPENFDA_INTEGRATION=1 to run live openFDA API tests",
)


@pytest.fixture
def agent() -> OpenFDAAgent:
    return OpenFDAAgent()


# --- Heuristic application detection (no LLM, no network) ---


@pytest.mark.parametrize(
    "user_query, expected_app",
    [
        ("Status of NDA-214766", "NDA214766"),
        ("ANDA 077890 approval", "ANDA077890"),
        ("See BLA125577 for biosimilar", "BLA125577"),
        ("application # NDA 123456", "NDA123456"),
        ("Application number: ANDA-987654", "ANDA987654"),
    ],
)
def test_heuristic_application_number(agent: OpenFDAAgent, user_query: str, expected_app: str) -> None:
    plan = agent._heuristic_search_plan(user_query)
    assert plan is not None
    assert plan["intent"] == "application"
    assert plan["application_number"] == expected_app
    assert plan.get("terms") == []


@pytest.mark.parametrize(
    "user_query",
    [
        "What is metformin used for?",
        "Pfizer oncology pipeline",
        "",
    ],
)
def test_heuristic_no_match(agent: OpenFDAAgent, user_query: str) -> None:
    assert agent._heuristic_search_plan(user_query) is None


# --- JSON plan parsing ---


def test_parse_llm_json_plan_raw(agent: OpenFDAAgent) -> None:
    raw = '{"intent": "drug_substance", "terms": ["nivolumab"], "application_number": null, "dosage_form": null, "route": null}'
    p = OpenFDAAgent._parse_llm_json_plan(raw)
    assert p is not None
    assert p["intent"] == "drug_substance"
    assert p["terms"] == ["nivolumab"]


def test_parse_llm_json_plan_fenced(agent: OpenFDAAgent) -> None:
    text = """Here you go:
```json
{"intent": "brand", "terms": ["Keytruda"]}
```
"""
    p = OpenFDAAgent._parse_llm_json_plan(text)
    assert p is not None
    assert p["intent"] == "brand"
    assert p["terms"] == ["Keytruda"]


def test_parse_llm_json_plan_embedded(agent: OpenFDAAgent) -> None:
    text = 'Sure. {"intent": "company", "terms": ["eli lilly", "lilly"]} trailing junk'
    p = OpenFDAAgent._parse_llm_json_plan(text)
    assert p is not None
    assert p["intent"] == "company"


# --- Plan normalization ---


def test_normalize_plan_unknown_intent(agent: OpenFDAAgent) -> None:
    n = agent._normalize_plan({"intent": "not_a_real_intent", "terms": ["x"]})
    assert n["intent"] == "general"
    assert n["terms"] == ["x"]


def test_normalize_plan_terms_string_with_or(agent: OpenFDAAgent) -> None:
    n = agent._normalize_plan({"intent": "general", "terms": "metformin OR insulin"})
    assert n["terms"] == ["metformin", "insulin"]


def test_normalize_plan_dedupes_terms(agent: OpenFDAAgent) -> None:
    n = agent._normalize_plan({"terms": ["aspirin", "Aspirin", "aspirin"]})
    assert n["terms"] == ["aspirin"]


# --- Fielded query detection ---


@pytest.mark.parametrize(
    "q, fielded",
    [
        ('openfda.brand_name:"X"', True),
        ("products.route:ORAL", True),
        ('products.route:"ORAL"', True),
        ("metformin tablets", False),
        ('application_number:"NDA123"', True),
        ('sponsor_name:"Pfizer"', True),
    ],
)
def test_looks_like_fielded(agent: OpenFDAAgent, q: str, fielded: bool) -> None:
    assert agent._looks_like_fielded_openfda_query(q) is fielded


# --- Strategy shapes by intent ---


def test_strategies_application_only_no_broad_tail(agent: OpenFDAAgent) -> None:
    plan = agent._normalize_plan(
        {"intent": "application", "application_number": "NDA020503", "terms": []}
    )
    strat = agent._build_strategies_from_plan(plan, "NDA 020503 status", lim=10)
    assert len(strat) >= 1
    assert strat[0]["search"] == 'application_number:"NDA020503"'
    searches = " ".join(s["search"] for s in strat)
    assert "diabetic" not in searches  # condition hints skipped for application-only


def test_strategies_company(agent: OpenFDAAgent) -> None:
    plan = agent._normalize_plan({"intent": "company", "terms": ["pfizer"]})
    strat = agent._build_strategies_from_plan(plan, "pfizer recent approvals", lim=10)
    joined = " | ".join(s["search"] for s in strat)
    assert "sponsor_name:" in joined
    assert "manufacturer_name:" in joined


def test_strategies_brand(agent: OpenFDAAgent) -> None:
    plan = agent._normalize_plan({"intent": "brand", "terms": ["keytruda"]})
    strat = agent._build_strategies_from_plan(plan, "keytruda label", lim=10)
    assert any("openfda.brand_name:" in s["search"] for s in strat)


def test_strategies_drug_substance(agent: OpenFDAAgent) -> None:
    plan = agent._normalize_plan({"intent": "drug_substance", "terms": ["pembrolizumab"]})
    strat = agent._build_strategies_from_plan(plan, "pembrolizumab", lim=10)
    assert any("openfda.generic_name:" in s["search"] for s in strat)


def test_strategies_drug_substance_two_tokens_single_or_chain(agent: OpenFDAAgent) -> None:
    plan = agent._normalize_plan({"intent": "drug_substance", "terms": ["empagliflozin", "linagliptin"]})
    strat = agent._build_strategies_from_plan(plan, "empagliflozin linagliptin combo", lim=10)
    primary = next(s for s in strat if "openfda.generic_name:" in s["search"])
    assert "empagliflozin" in primary["search"] and "linagliptin" in primary["search"]
    assert "+" in primary["search"]


def test_strategies_pharm_class(agent: OpenFDAAgent) -> None:
    plan = agent._normalize_plan({"intent": "pharm_class", "terms": ["sglt2"]})
    strat = agent._build_strategies_from_plan(plan, "SGLT2 inhibitors diabetes", lim=10)
    assert any("pharm_class_epc:" in s["search"] for s in strat)


def test_strategies_form_route(agent: OpenFDAAgent) -> None:
    plan = agent._normalize_plan(
        {
            "intent": "form_route",
            "terms": [],
            "dosage_form": "TABLET",
            "route": "ORAL",
        }
    )
    strat = agent._build_strategies_from_plan(plan, "oral tablets", lim=10)
    joined = " ".join(s["search"] for s in strat)
    assert 'products.dosage_form:"TABLET"' in joined
    assert 'products.route:"ORAL"' in joined


def test_strategies_general_adds_diabetes_hint(agent: OpenFDAAgent) -> None:
    plan = agent._normalize_plan({"intent": "general", "terms": ["metformin"]})
    strat = agent._build_strategies_from_plan(plan, "type 2 diabetes metformin", lim=10)
    joined = " ".join(s["search"] for s in strat)
    assert "diabetic" in joined or "insulin" in joined


def test_strategies_dedupes(agent: OpenFDAAgent) -> None:
    plan = agent._normalize_plan({"intent": "general", "terms": ["x"]})
    # Run twice same inputs — dedupe_strategies used inside build
    a = agent._build_strategies_from_plan(plan, "same", lim=10)
    b = agent._build_strategies_from_plan(plan, "same", lim=10)
    assert len(a) == len(b)
    seen = set()
    for s in a:
        key = (s["search"], s["limit"])
        assert key not in seen
        seen.add(key)


# --- Async: resolve plan with mocked LLM ---


@pytest.mark.asyncio
async def test_resolve_search_plan_heuristic_skips_llm(agent: OpenFDAAgent) -> None:
    with patch.object(
        agent,
        "_llm_search_plan",
        new_callable=AsyncMock,
    ) as mock_llm:
        plan = await agent._resolve_search_plan("Please check NDA-021920")
        assert plan["intent"] == "application"
        assert plan["application_number"] == "NDA021920"
        mock_llm.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_search_plan_uses_llm_when_no_heuristic(agent: OpenFDAAgent) -> None:
    fake_json = '{"intent": "company", "terms": ["novartis"], "application_number": null, "dosage_form": null, "route": null}'
    with patch.object(
        agent,
        "_llm_search_plan",
        new_callable=AsyncMock,
        return_value=agent._normalize_plan(agent._parse_llm_json_plan(fake_json)),
    ) as mock_llm:
        plan = await agent._resolve_search_plan("Who sponsors Kisqali at Novartis?")
        mock_llm.assert_called_once()
        assert plan["intent"] == "company"
        assert "novartis" in [t.lower() for t in plan["terms"]]


@pytest.mark.asyncio
async def test_resolve_alternative_plan_broadens_when_same(agent: OpenFDAAgent) -> None:
    prior = agent._normalize_plan({"intent": "brand", "terms": ["obscurebrandxyz"]})
    same = dict(prior)
    with patch.object(
        agent,
        "_llm_search_plan",
        new_callable=AsyncMock,
        return_value=same,
    ):
        alt = await agent._resolve_alternative_plan("trade name obscurebrandxyz", prior)
        assert alt["intent"] == "general"


# --- Plan cache key ---


def test_plan_cache_key_distinct(agent: OpenFDAAgent) -> None:
    p1 = agent._normalize_plan({"intent": "general", "terms": ["a"]})
    p2 = agent._normalize_plan({"intent": "general", "terms": ["b"]})
    assert OpenFDAAgent._plan_cache_key(p1, "q", 20) != OpenFDAAgent._plan_cache_key(p2, "q", 20)


# --- Live API (optional): fielded + substance plan ---


@pytest.mark.integration
@live_openfda
@pytest.mark.asyncio
async def test_live_fielded_search_metformin(agent: OpenFDAAgent) -> None:
    results = await agent.search_by_generic_name("metformin", max_results=3)
    assert len(results) >= 1
    assert results[0].application_number


@pytest.mark.integration
@live_openfda
@pytest.mark.asyncio
async def test_live_plan_drug_substance(agent: OpenFDAAgent) -> None:
    plan = agent._normalize_plan({"intent": "drug_substance", "terms": ["aspirin"]})
    results = await agent._search_openfda_drugs(
        OpenFDAAgent._plan_cache_key(plan, "aspirin", 5),
        5,
        plan=plan,
        sanitized_query="aspirin",
    )
    assert len(results) >= 1
