"""
Fast integration checks for china_regulatory wiring (no full engine import).

Validates that planner, executor, API labels, catalog, and frontend list stay in sync.
Run: pytest test_china_regulatory_integration.py -v
"""
from __future__ import annotations

from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent
REPO = BACKEND.parent


def _read(rel: str) -> str:
    return (BACKEND / rel).read_text(encoding="utf-8", errors="replace")


def test_dynamic_reasoning_engine_imports_and_registers_agent() -> None:
    text = _read("graph/dynamic_reasoning_engine.py")
    assert "from agents.china_regulatory_agent import china_regulatory_agent" in text
    assert '"china_regulatory": china_regulatory_agent' in text
    assert 'elif source == "china_regulatory"' in text
    assert "cde-nmpa → china_regulatory" in text
    assert "cde-nmpa → china_regulatory" in text and "ema-eu → ema_eu" in text


def test_dynamic_reasoning_fallback_mapping_includes_aliases() -> None:
    text = _read("graph/dynamic_reasoning_engine.py")
    assert '"china_regulatory_api": "china_regulatory"' in text
    assert 'elif mapped_source == "china_regulatory"' in text


def test_main_complete_lists_china_regulatory() -> None:
    text = _read("main_complete.py")
    assert '"china_regulatory":' in text


def test_data_catalog_includes_china_source() -> None:
    text = _read("services/data_catalog_service.py")
    assert "CDE / NMPA (China regulatory web)" in text


def test_frontend_regulatory_agent_id() -> None:
    path = REPO / "frontend" / "lib" / "data" / "agents.ts"
    if not path.is_file():
        pytest.skip("frontend agents.ts not present")
    text = path.read_text(encoding="utf-8", errors="replace")
    assert 'id: "cde-nmpa"' in text


@pytest.mark.skipif(
    __import__("os").environ.get("CHINA_FULL_ENGINE_TEST") != "1",
    reason="set CHINA_FULL_ENGINE_TEST=1 to instantiate DynamicReasoningEngine (slow, heavy imports)",
)
def test_dynamic_reasoning_engine_runtime_has_china_regulatory() -> None:
    from graph.dynamic_reasoning_engine import DynamicReasoningEngine

    eng = DynamicReasoningEngine()
    assert "china_regulatory" in eng.available_agents
    assert eng.available_agents["china_regulatory"] is not None
    agent = eng.available_agents["china_regulatory"]
    assert hasattr(agent, "search_regulatory")
    assert callable(getattr(agent, "search_regulatory"))
