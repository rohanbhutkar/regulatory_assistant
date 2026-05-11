"""ClinicalTrials.gov v2 query.term must stay under server 'Too complicated query' limits."""
from __future__ import annotations

from agents.clinical_trials_agent import (
    ClinicalTrialsAgent,
    _CTGOV_QUERY_TERM_MAX_TOKENS,
)


def test_studies_params_cap_long_keyword_query() -> None:
    agent = ClinicalTrialsAgent()
    q = (
        "tirzepatide mounjaro gip glp-1 nash nonalcoholic steatohepatitis nafld "
        "non-alcoholic steatohepatitis liver fat"
    )
    params = agent._studies_list_params(q, 30)
    term = params.get("query.term", "")
    assert term
    assert len(term.split()) <= _CTGOV_QUERY_TERM_MAX_TOKENS


def test_cap_dedupes_case_insensitive() -> None:
    assert ClinicalTrialsAgent._cap_ctgov_query_term("Foo foo BAR bar xx") == "Foo BAR xx"


def test_keyword_query_term_respects_max() -> None:
    raw = " ".join(f"drug{n:03d}xx" for n in range(25))
    out = ClinicalTrialsAgent._keyword_query_term(raw)
    assert len(out.split()) <= _CTGOV_QUERY_TERM_MAX_TOKENS
