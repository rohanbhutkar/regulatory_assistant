"""Smoke checks: graph agent registry + auxiliary agent modules import."""
from __future__ import annotations

import importlib

import pytest


def test_dynamic_reasoning_engine_registry() -> None:
    from graph.dynamic_reasoning_engine import DynamicReasoningEngine

    eng = DynamicReasoningEngine()
    lazy = {"claims_data", "payer_data", "healthcare_analytics", "hitl_trial_selection"}
    for name, agent in eng.available_agents.items():
        if name in lazy:
            assert agent is None, f"{name} should be lazily unset at init"
        else:
            assert agent is not None, f"missing agent: {name}"


@pytest.mark.parametrize(
    "module",
    [
        "agents.insights_agent",
        "agents.soa_extractor_agent",
        "agents.protocol_authoring_agent",
        "agents.enhanced_protocol_authoring_agent",
        "agents.asset_strategy_agent",
        "agents.hitl_agent",
        "agents.ema_epi_client",
        "agents.ema_pms_client",
        "agents.ema_json_index",
        "agents.ema_query_router",
    ],
)
def test_auxiliary_agent_module_imports(module: str) -> None:
    importlib.import_module(module)


def test_payer_and_healthcare_analytics_import() -> None:
    """Payer CSVs live under repo-root data/payer_data (path fixed for this repo layout)."""
    importlib.import_module("agents.payer_data_agent")
    importlib.import_module("agents.healthcare_analytics_agent")
