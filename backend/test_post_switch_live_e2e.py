"""
Post-switch live checks: ClinicalTrials.gov v2 (long query), optional AACT SSL.

Does not call OpenAI. Uses real network / DB when env is set.

Run from backend:
  pytest test_post_switch_live_e2e.py -v
"""
from __future__ import annotations

import pytest

from config import settings


@pytest.mark.asyncio
async def test_clinicaltrials_api_long_query_not_400() -> None:
    """Previously ~11 AND tokens caused HTTP 400 'Too complicated query'."""
    from agents.clinical_trials_agent import ClinicalTrialsAgent

    agent = ClinicalTrialsAgent()
    q = (
        "tirzepatide mounjaro gip glp-1 nash nonalcoholic steatohepatitis nafld "
        "non-alcoholic steatohepatitis liver fat"
    )
    params = agent._studies_list_params(q, 10)
    assert "query.term" in params
    assert len((params.get("query.term") or "").split()) <= 10

    # Live call must succeed (200); ANDed capped terms may legitimately return 0 hits.
    results = await agent._search_studies_api(q, max_results=5)
    assert isinstance(results, list)

    simple = await agent._search_studies_api("tirzepatide", max_results=5)
    assert len(simple) >= 1, "CT.gov should return hits for a simple drug term"


@pytest.mark.asyncio
async def test_aact_simple_query_when_configured() -> None:
    """AACT: SSL + credentials; skips if not configured."""
    from agents.aact_agent import aact_agent

    if not aact_agent.enabled:
        pytest.skip("AACT credentials not set")

    res = await aact_agent.execute_custom_query("SELECT 1 AS one;", [])
    if not res.get("success"):
        err = str(res.get("error") or "")
        if "CERTIFICATE_VERIFY_FAILED" in err or "certificate" in err.lower():
            pytest.skip(f"AACT TLS from this environment: {err[:200]}")
        pytest.fail(err)
    rows = res.get("results") or []
    assert len(rows) == 1 and int(rows[0].get("one", 0)) == 1


@pytest.mark.asyncio
async def test_structured_response_anthropic_json_shape() -> None:
    """Sanity: structured JSON-ish output (path that logged 'Empty response text' on OpenAI)."""
    if (settings.LLM_PROVIDER or "").lower().strip() != "anthropic":
        pytest.skip("LLM_PROVIDER is not anthropic")
    if not (settings.ANTHROPIC_API_KEY or "").strip():
        pytest.skip("ANTHROPIC_API_KEY not set")

    from agents.llm_agent import LLMAgent

    agent = LLMAgent()
    raw = await agent.generate_structured_response(
        'Return ONLY valid JSON: {"ok": true, "word": "pong"}',
        system_prompt="Output JSON only, no markdown fences.",
        max_tokens=128,
    )
    assert raw and "empty response" not in raw.lower(), raw[:500]
    assert "pong" in raw.lower() or '"ok"' in raw.lower(), raw[:500]
