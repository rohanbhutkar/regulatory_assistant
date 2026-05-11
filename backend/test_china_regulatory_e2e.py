#!/usr/bin/env python3
"""
Optional e2e checks for china_regulatory (Google CSE + fetches).

Requires GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID (or GOOGLE_CSE_CHINA_ENGINE_ID).

Run from backend:
  python3 test_china_regulatory_e2e.py
  CHINA_E2E_BASE_URL=http://127.0.0.1:8001 python3 test_china_regulatory_e2e.py

Note: Importing DynamicReasoningEngine can take ~1–2 minutes (full agent graph). For fast wiring checks:
  pytest test_china_regulatory_integration.py -v
"""
from __future__ import annotations

import asyncio
import os
import sys


def _test_engine_wiring() -> None:
    from graph.dynamic_reasoning_engine import DynamicReasoningEngine

    eng = DynamicReasoningEngine()
    assert "china_regulatory" in eng.available_agents, "china_regulatory missing from available_agents"
    assert eng.available_agents["china_regulatory"] is not None, "china_regulatory agent is None"
    print("OK: DynamicReasoningEngine has active china_regulatory")


async def _test_agent_search() -> None:
    key = (os.environ.get("GOOGLE_API_KEY") or "").strip()
    cx = (os.environ.get("GOOGLE_CSE_CHINA_ENGINE_ID") or os.environ.get("GOOGLE_SEARCH_ENGINE_ID") or "").strip()
    if not key or not cx:
        print("SKIP: live CSE (set GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID)")
        return

    from agents.china_regulatory_agent import china_regulatory_agent

    results = await china_regulatory_agent.search_regulatory(
        "指导原则 药审中心", "official CDE or NMPA pages", max_results=3
    )
    assert isinstance(results, list), "search_regulatory must return a list"
    print(f"OK: china_regulatory_agent.search_regulatory returned {len(results)} hits")
    for r in results[:3]:
        print(f"   - [{r.metadata.get('portal')}] {r.url[:70]}...")


async def _test_live_http() -> None:
    base = os.environ.get("CHINA_E2E_BASE_URL", "").strip().rstrip("/")
    if not base:
        print("SKIP: live HTTP (set CHINA_E2E_BASE_URL=http://127.0.0.1:8001 to run)")
        return

    import httpx

    timeout = httpx.Timeout(15.0)
    async with httpx.AsyncClient(base_url=base, timeout=timeout) as client:
        r = await client.get("/api/agents")
        r.raise_for_status()
        data = r.json()
        agents = data.get("agents", {})
        assert "china_regulatory" in agents, "/api/agents must list china_regulatory"
        assert agents["china_regulatory"].get("active") is True, "china_regulatory should be active"
        print(f"OK: GET {base}/api/agents includes china_regulatory active")


async def main() -> None:
    _test_engine_wiring()
    await _test_agent_search()
    await _test_live_http()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except AssertionError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)
