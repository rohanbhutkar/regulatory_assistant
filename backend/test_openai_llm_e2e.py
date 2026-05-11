"""
Live OpenAI smoke test (one short completion).

Requires LLM_PROVIDER=openai and OPENAI_API_KEY. Skips otherwise.
Run from backend:
  pytest test_openai_llm_e2e.py -v
"""
from __future__ import annotations

import pytest

from config import settings


@pytest.mark.asyncio
async def test_openai_live_short_completion() -> None:
    if (settings.LLM_PROVIDER or "").lower().strip() != "openai":
        pytest.skip("LLM_PROVIDER is not openai")
    if not (settings.OPENAI_API_KEY or "").strip():
        pytest.skip("OPENAI_API_KEY not set")

    from agents.llm_agent import LLMAgent

    agent = LLMAgent()
    assert agent.provider == "openai"
    assert agent.model == (settings.OPENAI_MODEL or "gpt-5-mini").strip()

    out = await agent.generate_response(
        'Reply with exactly one word: pong',
        system_prompt="Follow the user format exactly.",
        max_tokens=32,
    )
    assert out and "error generating response" not in out.lower(), out[:500]
    assert "pong" in out.lower(), out[:500]
