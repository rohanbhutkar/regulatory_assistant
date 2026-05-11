"""Unit tests for OpenAI chat response parsing helpers."""
from __future__ import annotations

from types import SimpleNamespace

from agents.llm_agent import _openai_parse_chat_assistant_text


def test_parse_normal_content() -> None:
    msg = SimpleNamespace(content="  hello  ", refusal=None)
    ch = SimpleNamespace(message=msg, finish_reason="stop")
    resp = SimpleNamespace(choices=[ch])
    c, fr, r = _openai_parse_chat_assistant_text(resp)
    assert c == "hello"
    assert fr == "stop"
    assert r == ""


def test_parse_refusal_when_content_empty() -> None:
    msg = SimpleNamespace(content=None, refusal="Policy block")
    ch = SimpleNamespace(message=msg, finish_reason="stop")
    resp = SimpleNamespace(choices=[ch])
    c, fr, r = _openai_parse_chat_assistant_text(resp)
    assert c == ""
    assert r == "Policy block"


def test_parse_no_choices() -> None:
    resp = SimpleNamespace(choices=[])
    assert _openai_parse_chat_assistant_text(resp) == ("", None, "")
