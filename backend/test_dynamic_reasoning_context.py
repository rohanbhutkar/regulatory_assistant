"""
Unit tests for context truncation and ContextManager synthesis formatting.

Run from backend:
  pytest test_dynamic_reasoning_context.py -q
"""
from __future__ import annotations

import pytest

from graph import truncation_utils as tu
from models.schemas import ContextItem, ContextManager


SEP = "=" * 80


def test_progressive_truncation_preserves_all_sections():
    """Every split section must appear in output (no early break dropping tail)."""
    middle_a = "A" * 9000
    middle_b = "B" * 9000
    middle_c = "C" * 9000
    header = "HEADER\nkeep instructions visible"
    footer = "INSTRUCTIONS:\n1. Do the thing.\n2. Cite sources.\nCOMPREHENSIVE ANSWER:\n"
    prompt = f"{header}\n{SEP}\n{middle_a}\n{SEP}\n{middle_b}\n{SEP}\n{middle_c}\n{SEP}\n{footer}"

    assert prompt.count(SEP) == 4
    out = tu.progressive_truncation(prompt, target_tokens=4000)
    parts = out.split(SEP)
    assert len(parts) == 5, f"expected 5 sections, got {len(parts)}"
    assert "HEADER" in parts[0]
    assert "INSTRUCTIONS:" in parts[-1]
    assert "A" in parts[1] or "[Section truncated" in parts[1]
    assert "B" in parts[2] or "[Section truncated" in parts[2]
    assert "C" in parts[3] or "[Section truncated" in parts[3]


def test_progressive_truncation_under_budget_unchanged():
    small = f"Hi{SEP}mid{SEP}tail"
    assert tu.progressive_truncation(small, target_tokens=100_000) == small


def test_progressive_truncation_few_sections_fallback():
    big = "word. " * 5000
    out = tu.progressive_truncation(big, target_tokens=500)
    assert len(out) < len(big)
    assert "truncated" in out.lower()


def test_emergency_truncation_reduces_and_adds_sentinel():
    big = '{"a":' + '"x",' * 2000 + '"z":1}'
    out = tu.emergency_truncation(big, target_tokens=800)
    assert tu.estimate_tokens(out) <= tu.estimate_tokens(big)
    assert "EMERGENCY TRUNCATION" in out


def test_calculate_dynamic_limits_under_budget_returns_full_counts():
    small = {
        "trial_summaries": [{"nct_id": "NCT1", "summary": "s"}],
        "soa_table_details": [{"table_data": [1]}],
    }
    lim = tu.calculate_dynamic_limits(small, target_max_tokens=500_000)
    assert lim["trial_summaries"] == 1
    assert lim["soa_table_details"] == 1


def test_calculate_dynamic_limits_over_budget_reduces():
    huge = {
        "trial_summaries": [{"nct_id": f"NCT{i}", "summary": "x" * 2000} for i in range(50)],
        "soa_table_details": [{"table_data": list(range(100))} for _ in range(30)],
    }
    lim = tu.calculate_dynamic_limits(huge, target_max_tokens=5_000)
    assert lim["trial_summaries"] < 50
    assert lim["soa_table_details"] < 30
    assert lim["trial_summaries"] >= 1
    assert lim["soa_table_details"] >= 1


def test_get_context_for_synthesis_respects_layer_budget():
    cm = ContextManager(query="diabetes trial oncology")
    long_analysis = "Analysis paragraph. " * 400
    cm.add_context_item(
        layer_type="analysis",
        content={
            "analysis": long_analysis,
            "node_id": "n1",
        },
        source="llm_analysis",
        node_id="n1",
    )
    out = cm.get_context_for_synthesis(max_items_per_layer=5, layer_char_budget=2500)
    assert "ANALYSIS LAYER" in out
    assert len(out) <= 6000
    assert "Analysis paragraph" in out


def test_format_context_item_compact_nct_reference():
    cm = ContextManager(query="q")
    item = ContextItem(
        id="1",
        content={"nct_id": "NCT01234567", "title": "A study", "condition": "X"},
        source="aact",
        node_id="s1",
        timestamp=0.0,
        context_type="search",
    )
    line = cm._format_context_item(item, max_body_chars=500, compact_nct_ids={"NCT01234567"})
    assert "NCT01234567" in line
    assert "STRUCTURED_TRIAL" in line or "below" in line.lower()


def test_format_context_item_preserves_analysis_when_budget_large():
    cm = ContextManager(query="q")
    body = "KEYFINDING " * 50
    item = ContextItem(
        id="2",
        content={"analysis": body, "node_id": "a1"},
        source="llm",
        node_id="a1",
        timestamp=0.0,
        context_type="analysis",
    )
    short = cm._format_context_item(item, max_body_chars=120)
    long_fmt = cm._format_context_item(item, max_body_chars=5000)
    assert len(long_fmt) > len(short)
    assert "KEYFINDING" in long_fmt
