"""
BM25-based retrieval over context items to widen the candidate pool before formatting.
"""
from __future__ import annotations

from typing import List, TYPE_CHECKING

from utils.bm25 import bm25_scores

if TYPE_CHECKING:
    from models.schemas import ContextItem


def rank_items_by_query(query: str, items: List["ContextItem"]) -> List["ContextItem"]:
    """Return items sorted by BM25 score descending (best first)."""
    if not items or not query.strip():
        return list(items)
    docs = [str(it.content) for it in items]
    scores = bm25_scores(query, docs)
    order = sorted(range(len(items)), key=lambda i: scores[i], reverse=True)
    return [items[i] for i in order]
