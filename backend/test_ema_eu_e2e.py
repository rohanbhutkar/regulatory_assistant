#!/usr/bin/env python3
"""
End-to-end checks for the EMA / EU medicines agent (ema_eu).

1. Engine wiring: DynamicReasoningEngine exposes ema_eu.
2. Data path: ema_eu_agent.search returns EmaSearchResult rows from EMA JSON (network).
3. Optional live API: if EMA_E2E_BASE_URL=http://127.0.0.1:8001, GET /api/agents and POST /api/research/query.

Run from backend directory:
  python test_ema_eu_e2e.py
  EMA_E2E_BASE_URL=http://127.0.0.1:8001 python test_ema_eu_e2e.py
"""
from __future__ import annotations

import asyncio
import os
import sys


def _test_engine_wiring() -> None:
    from graph.dynamic_reasoning_engine import DynamicReasoningEngine

    eng = DynamicReasoningEngine()
    assert "ema_eu" in eng.available_agents, "ema_eu missing from available_agents"
    assert eng.available_agents["ema_eu"] is not None, "ema_eu agent is None"
    print("OK: DynamicReasoningEngine has active ema_eu")


async def _test_agent_search() -> None:
    from agents.ema_eu_agent import ema_eu_agent

    results = await ema_eu_agent.search("Ozempic EU centralised authorisation", max_results=5)
    assert isinstance(results, list), "search must return a list"
    assert len(results) >= 1, "expected at least one EMA JSON hit for Ozempic"
    subs = {r.sub_source for r in results}
    print(f"OK: ema_eu_agent.search returned {len(results)} hits, sub_sources={subs}")
    for r in results[:3]:
        print(f"   - [{r.sub_source}] {r.title[:70]}...")


async def _test_live_http() -> None:
    base = os.environ.get("EMA_E2E_BASE_URL", "").strip().rstrip("/")
    if not base:
        print("SKIP: live HTTP (set EMA_E2E_BASE_URL=http://127.0.0.1:8001 to run)")
        return

    import httpx

    timeout = httpx.Timeout(15.0)
    async with httpx.AsyncClient(base_url=base, timeout=timeout) as client:
        r = await client.get("/api/agents")
        r.raise_for_status()
        data = r.json()
        agents = data.get("agents", {})
        assert "ema_eu" in agents, "/api/agents must list ema_eu"
        assert agents["ema_eu"].get("active") is True, "ema_eu should be active"
        print(f"OK: GET {base}/api/agents includes ema_eu active")

        # Full orchestration needs LLM; keep query narrow and EU-only so planner may use ema_eu when selected_agents set.
        body = {
            "query": "Summarise EU EMA marketing authorisation status for Ozempic using only EMA sources.",
            "selected_agents": ["ema-eu"],
        }
        r2 = await client.post("/api/research/query", json=body)
        if r2.status_code != 200:
            print(f"WARN: POST /api/research/query -> {r2.status_code} {r2.text[:500]}")
            return
        payload = r2.json()
        assert payload.get("success") is True
        syn = payload.get("synthesis") or {}
        answer = (syn.get("summary") or syn.get("answer") or "")[:200]
        print(f"OK: POST /api/research/query completed (synthesis excerpt): {answer!r}...")


async def _test_live_websocket() -> None:
    base = os.environ.get("EMA_E2E_BASE_URL", "").strip().rstrip("/")
    if not base:
        print("SKIP: WebSocket (set EMA_E2E_BASE_URL)")
        return
    ws_url = base.replace("http://", "ws://").replace("https://", "wss://") + "/ws/e2e-test-ema"
    try:
        import websockets
    except ImportError:
        print("SKIP: websockets package not installed")
        return

    import json

    async with websockets.connect(ws_url, close_timeout=5) as ws:
        await ws.send(
            json.dumps(
                {
                    "type": "query",
                    "data": {
                        "query": "EU EMA status for Ozempic",
                        "selected_agents": ["ema-eu"],
                        "conversation_history": [],
                    },
                }
            )
        )
        # Wait for query_completed (may take minutes if LLM runs)
        timeout_s = float(os.environ.get("EMA_E2E_WS_TIMEOUT", "180"))
        while timeout_s > 0:
            raw = await asyncio.wait_for(ws.recv(), timeout=min(30.0, timeout_s))
            timeout_s -= 30.0
            msg = json.loads(raw)
            if msg.get("type") == "query_completed":
                print("OK: WebSocket query_completed received")
                return
            if msg.get("type") == "error":
                raise AssertionError(f"WebSocket error: {msg}")
        raise AssertionError("timeout waiting for query_completed")


async def main() -> None:
    _test_engine_wiring()
    await _test_agent_search()
    await _test_live_http()
    if os.environ.get("EMA_E2E_WS", "").lower() in ("1", "true", "yes"):
        await _test_live_websocket()
    print("\nAll non-skipped E2E checks passed.")


if __name__ == "__main__":
    asyncio.run(main())
    sys.exit(0)
