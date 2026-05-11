"""
Live Anthropic smoke test (one short completion).

Requires LLM_PROVIDER=anthropic and ANTHROPIC_API_KEY. Skips otherwise.
Run from backend:
  pytest test_anthropic_llm_e2e.py -v
"""
from __future__ import annotations

import pytest

from config import settings


@pytest.mark.asyncio
async def test_anthropic_live_short_completion() -> None:
    if (settings.LLM_PROVIDER or "").lower().strip() != "anthropic":
        pytest.skip("LLM_PROVIDER is not anthropic")
    if not (settings.ANTHROPIC_API_KEY or "").strip():
        pytest.skip("ANTHROPIC_API_KEY not set")

    from agents.llm_agent import LLMAgent

    agent = LLMAgent()
    assert agent.provider == "anthropic"
    expected = (settings.ANTHROPIC_MODEL or "").strip() or "claude-sonnet-4-6"
    assert agent.model == expected

    out = await agent.generate_response(
        "Reply with exactly one word: pong",
        system_prompt="Follow the user format exactly.",
        max_tokens=64,
    )
    assert out and "error generating response" not in out.lower(), out[:500]
    assert "pong" in out.lower(), out[:500]
