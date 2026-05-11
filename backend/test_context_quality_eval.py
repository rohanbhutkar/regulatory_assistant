"""
Lightweight context-quality checks (no LLM). Run: pytest test_context_quality_eval.py -q
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from context_compression import CompressionBrief, parse_compression_brief_llm_output
from models.schemas import ContextItem, ContextManager
from utils.bm25 import bm25_scores
from utils.token_counting import estimate_tokens

CASES_PATH = Path(__file__).resolve().parent / "eval" / "context_quality_cases.json"


def _load_cases():
    raw = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    return raw


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
def test_eval_case(case: dict):
    cm = ContextManager(query=case["query"])
    for spec in case.get("context_items", []):
        cm.add_context_item(
            layer_type=spec.get("layer_type", "search"),
            content=spec["content"],
            source="eval",
            node_id="eval",
        )

    if "expect_substrings" in case:
        cm.calculate_attention_weights(method="keyword")
        out = cm.get_context_for_synthesis(max_items_per_layer=5, layer_char_budget=8000, bm25_pool_factor=1)
        for s in case["expect_substrings"]:
            assert s in out, f"missing {s!r} in context output"

    if case.get("expect_first_nct_after_bm25_pool"):
        layer = cm.layers[0]
        from context_retrieval import rank_items_by_query

        ranked = rank_items_by_query(case["query"], list(layer.items))
        top = ranked[0].content.get("nct_id") if isinstance(ranked[0].content, dict) else None
        assert top == case["expect_first_nct_after_bm25_pool"]


def test_compression_brief_parse_roundtrip():
    brief = CompressionBrief(
        claims=["a"],
        verbatim_quotes=[{"source_id": "NCT1", "quote": "hello"}],
        citations=["NCT1"],
        gaps=["x"],
    )
    parsed = parse_compression_brief_llm_output(brief.model_dump_json())
    assert parsed is not None
    assert parsed.citations == ["NCT1"]


def test_tiktoken_estimate_ordering():
    a = "hello " * 100
    b = "hello " * 200
    assert estimate_tokens(b) > estimate_tokens(a)


def test_bm25_scores_basic():
    q = "lung cancer trial"
    docs = ["diabetes study", "non-small cell lung cancer phase 2"]
    s = bm25_scores(q, docs)
    assert s[1] > s[0]
