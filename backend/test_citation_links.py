"""Unit tests for citation_links helpers."""
from utils.citation_links import (
    citation_link_from_content,
    clinicaltrials_url,
    dedupe_citation_links,
    normalize_citation_entries,
    pubmed_url,
)


def test_clinicaltrials_url():
    assert "NCT12345678" in clinicaltrials_url("NCT12345678")
    assert clinicaltrials_url("12345678").endswith("NCT12345678")


def test_pubmed_url():
    assert pubmed_url("12345") == "https://pubmed.ncbi.nlm.nih.gov/12345/"


def test_citation_link_nct():
    link = citation_link_from_content(
        {"nct_id": "NCT04280705", "title": "Example trial", "phase": "2"},
        "search",
    )
    assert link
    assert "clinicaltrials.gov" in link["url"]
    assert "NCT04280705" in link["text"]


def test_citation_link_web():
    link = citation_link_from_content(
        {
            "url": "https://www.fda.gov/foo",
            "title": "Guidance",
            "source_domain": "fda.gov",
        },
        "search",
    )
    assert link["url"] == "https://www.fda.gov/foo"
    assert "Guidance" in link["text"]


def test_normalize_and_dedupe():
    raw = [
        "See https://example.com/a for details",
        {"text": "Same", "url": "https://example.com/a"},
        {"text": "Other", "url": ""},
    ]
    out = normalize_citation_entries(raw)
    assert len(out) >= 2
    urls = [x["url"] for x in out if x["url"]]
    assert "https://example.com/a" in urls


def test_dedupe_citation_links():
    d = dedupe_citation_links(
        [
            {"text": "A", "url": "https://x.com"},
            {"text": "A", "url": "https://x.com"},
            {"text": "B", "url": ""},
        ]
    )
    assert len(d) == 2
