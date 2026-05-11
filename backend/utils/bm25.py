"""
Lightweight BM25 (Okapi) for query–document relevance without extra dependencies.
"""
from __future__ import annotations

import math
import re
from typing import List, Sequence


_token_re = re.compile(r"[a-z0-9]+", re.I)


def tokenize(text: str) -> List[str]:
    return _token_re.findall((text or "").lower())


def _build_index(docs: Sequence[Sequence[str]]):
    df = {}
    doc_lens = []
    for toks in docs:
        doc_lens.append(len(toks) or 1)
        seen = set(toks)
        for t in seen:
            df[t] = df.get(t, 0) + 1
    n_docs = len(docs) or 1
    idf = {}
    for t, freq in df.items():
        idf[t] = math.log(1.0 + (n_docs - freq + 0.5) / (freq + 0.5))
    avgdl = sum(doc_lens) / max(1, len(doc_lens))
    return idf, doc_lens, avgdl, n_docs


def bm25_scores(query: str, documents: Sequence[str], k1: float = 1.5, b: float = 0.75) -> List[float]:
    """Return BM25 score per document (same order as `documents`)."""
    if not documents:
        return []
    q_toks = tokenize(query)
    if not q_toks:
        return [0.0] * len(documents)
    doc_toks = [tokenize(d) for d in documents]
    idf, doc_lens, avgdl, _ = _build_index(doc_toks)
    scores = []
    for toks, dl in zip(doc_toks, doc_lens):
        tf = {}
        for t in toks:
            tf[t] = tf.get(t, 0) + 1
        s = 0.0
        for qt in q_toks:
            if qt not in tf:
                continue
            idf_q = idf.get(qt, 0.0)
            f = tf[qt]
            denom = f + k1 * (1 - b + b * dl / avgdl)
            s += idf_q * (f * (k1 + 1)) / denom
        scores.append(s)
    return scores


def normalize_scores(scores: List[float]) -> List[float]:
    if not scores:
        return []
    m = max(scores) or 1e-9
    return [min(1.0, x / m) for x in scores]
