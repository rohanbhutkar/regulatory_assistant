"""Tests for live HTTP API agents: mocked unit tests + optional real-network smoke tests.

Mocked tests (default):
  pytest test_live_api_agents.py -v

Real APIs (requires network; be polite to upstream rate limits):
  LIVE_API_AGENTS_INTEGRATION=1 pytest test_live_api_agents.py -v -m live_api

Optional: FDA Data Dashboard live check (needs keys):
  LIVE_API_AGENTS_INTEGRATION=1 plus FDA_DATADASHBOARD_USER and FDA_DATADASHBOARD_KEY set in env.
"""
from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _live_api_integration_enabled() -> bool:
    return os.getenv("LIVE_API_AGENTS_INTEGRATION", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _fda_dd_configured() -> bool:
    u = (os.getenv("FDA_DATADASHBOARD_USER") or "").strip()
    k = (os.getenv("FDA_DATADASHBOARD_KEY") or "").strip()
    return bool(u and k)


# --- Mocked unit tests ---


@pytest.mark.asyncio
async def test_nih_reporter_agent_parses_results():
    mock_data = {
        "results": [
            {
                "project_title": "Test grant",
                "core_project_num": "1R01HG999999",
                "organization": {"org_name": "Example University"},
            }
        ]
    }
    with patch("agents.nih_reporter_agent.httpx.AsyncClient") as m:
        inst = AsyncMock()
        m.return_value.__aenter__.return_value = inst
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value=mock_data)
        inst.post = AsyncMock(return_value=resp)
        from agents.nih_reporter_agent import NihReporterAgent

        agent = NihReporterAgent()
        out = await agent.search("oncology", max_results=5)
    assert len(out) == 1
    assert "test grant" in out[0].title.lower()
    d = out[0].model_dump() if hasattr(out[0], "model_dump") else out[0].dict()
    assert "url" in d


@pytest.mark.asyncio
async def test_npi_registry_agent_parses_results():
    mock_data = {
        "result_count": 1,
        "results": [
            {
                "number": "1234567890",
                "enumeration_type": "NPI-2",
                "basic": {"organization_name": "Test Hospital"},
                "addresses": [{"address_1": "1 Main", "city": "Boston", "state": "MA"}],
            }
        ],
    }
    with patch("agents.npi_registry_agent.httpx.AsyncClient") as m:
        inst = AsyncMock()
        m.return_value.__aenter__.return_value = inst
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value=mock_data)
        inst.get = AsyncMock(return_value=resp)
        from agents.npi_registry_agent import NpiRegistryAgent

        out = await NpiRegistryAgent().search("Test Hospital", max_results=5)
    assert len(out) == 1
    assert "test hospital" in out[0].title.lower()


@pytest.mark.asyncio
async def test_openalex_agent_parses_works():
    mock_data = {
        "results": [
            {
                "id": "https://openalex.org/W123",
                "display_name": "Example paper",
                "publication_year": 2024,
                "doi": "https://doi.org/10.1234/example",
            }
        ]
    }
    with patch("agents.openalex_agent.httpx.AsyncClient") as m:
        inst = AsyncMock()
        m.return_value.__aenter__.return_value = inst
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value=mock_data)
        inst.get = AsyncMock(return_value=resp)
        from agents.openalex_agent import OpenAlexAgent

        out = await OpenAlexAgent().search("diabetes", max_results=3)
    assert len(out) == 1
    assert "doi.org" in out[0].url


@pytest.mark.asyncio
async def test_crossref_agent_parses_items():
    mock_data = {"message": {"items": [{"title": ["CR Title"], "DOI": "10.1000/xyz", "type": "journal-article"}]}}
    with patch("agents.crossref_agent.httpx.AsyncClient") as m:
        inst = AsyncMock()
        m.return_value.__aenter__.return_value = inst
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value=mock_data)
        inst.get = AsyncMock(return_value=resp)
        from agents.crossref_agent import CrossrefAgent

        out = await CrossrefAgent().search("trial", max_results=2)
    assert len(out) == 1
    assert out[0].metadata.get("doi") == "10.1000/xyz"


@pytest.mark.asyncio
async def test_ror_agent_parses_items():
    mock_data = {
        "items": [
            {
                "id": "https://ror.org/03vek6s52",
                "name": "Harvard University",
                "locations": [{"country_code": "US"}],
            }
        ]
    }
    with patch("agents.ror_agent.httpx.AsyncClient") as m:
        inst = AsyncMock()
        m.return_value.__aenter__.return_value = inst
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value=mock_data)
        inst.get = AsyncMock(return_value=resp)
        from agents.ror_agent import RorAgent

        out = await RorAgent().search("Harvard", max_results=3)
    assert len(out) == 1
    assert "harvard" in out[0].title.lower()


@pytest.mark.asyncio
async def test_eu_ctis_agent_parses_data():
    mock_data = {
        "data": [
            {"ctNumber": "2024-518143-38-00", "ctTitle": "Example EU trial", "sponsor": "ACME"}
        ]
    }
    with patch("agents.eu_ctis_agent.httpx.AsyncClient") as m:
        inst = AsyncMock()
        m.return_value.__aenter__.return_value = inst
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value=mock_data)
        inst.post = AsyncMock(return_value=resp)
        from agents.eu_ctis_agent import EuCtisAgent

        out = await EuCtisAgent().search("oncology", max_results=5)
    assert len(out) == 1
    assert "eu trial" in out[0].title.lower() or "example" in out[0].title.lower()


@pytest.mark.asyncio
async def test_isrctn_agent_parses_who_xml():
    xml_body = """<?xml version="1.0" encoding="UTF-8"?>
<trials><trial><main>
  <trial_id>ISRCTN12345678</trial_id>
  <public_title>Diabetes study example</public_title>
  <url>https://www.isrctn.com/ISRCTN12345678</url>
</main></trial></trials>"""
    with patch("agents.isrctn_agent.httpx.AsyncClient") as m:
        inst = AsyncMock()
        m.return_value.__aenter__.return_value = inst
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.text = xml_body
        inst.get = AsyncMock(return_value=resp)
        from agents.isrctn_agent import IsrctnAgent

        out = await IsrctnAgent().search("diabetes", max_results=5)
    assert len(out) == 1
    assert "diabetes" in out[0].title.lower()


@pytest.mark.asyncio
async def test_cms_open_data_agent_filters_rows():
    rows = [
        {"ORGANIZATION NAME": "Johns Hopkins Hospital", "NPI": "111", "CITY": "Baltimore", "STATE": "MD"},
        {"ORGANIZATION NAME": "Other Clinic", "NPI": "222", "CITY": "X", "STATE": "YY"},
    ]
    with patch("agents.cms_open_data_agent.httpx.AsyncClient") as m:
        inst = AsyncMock()
        m.return_value.__aenter__.return_value = inst
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value=rows)
        inst.get = AsyncMock(return_value=resp)
        from agents.cms_open_data_agent import CmsOpenDataAgent

        out = await CmsOpenDataAgent().search("Johns Hopkins", max_results=10)
    assert len(out) >= 1
    assert "hopkins" in out[0].title.lower()


@pytest.mark.asyncio
async def test_open_payments_agent_metastore_match():
    datasets = [
        {"title": "General Payments", "identifier": "ds-1", "description": "Physician payments"},
        {"title": "Unrelated Dataset", "identifier": "ds-2", "description": "Other"},
    ]
    with patch("agents.open_payments_agent.httpx.AsyncClient") as m:
        inst = AsyncMock()
        m.return_value.__aenter__.return_value = inst
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value=datasets)
        inst.get = AsyncMock(return_value=resp)
        from agents.open_payments_agent import OpenPaymentsAgent

        agent = OpenPaymentsAgent()
        agent._resource_ids = []
        out = await agent.search("physician payment", max_results=10)
    titles = [x.title.lower() for x in out]
    assert any("general" in t or "payment" in t for t in titles)


@pytest.mark.asyncio
async def test_fda_datadashboard_no_credentials():
    from agents.fda_datadashboard_agent import FdaDatadashboardAgent
    from config import settings

    with patch.object(settings, "FDA_DATADASHBOARD_USER", ""), patch.object(
        settings, "FDA_DATADASHBOARD_KEY", ""
    ):
        agent = FdaDatadashboardAgent()
        out = await agent.search("inspection", max_results=5)
    assert len(out) == 1
    assert "fda_datadashboard" in out[0].content.lower()


# --- Optional live HTTP smoke tests (set LIVE_API_AGENTS_INTEGRATION=1) ---


async def _smoke_search(label: str, coro, timeout: float = 60.0):
    """Run one live search; skip on timeout/error/empty (flaky public APIs)."""
    try:
        out = await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        pytest.skip(f"{label}: timeout after {timeout}s")
    except Exception as e:
        pytest.skip(f"{label}: {type(e).__name__}: {e}")
    assert isinstance(out, list), f"{label}: expected list"
    if len(out) == 0:
        pytest.skip(f"{label}: zero results (query or upstream)")
    assert out[0].title, f"{label}: missing title"
    assert out[0].url, f"{label}: missing url"


@pytest.mark.live_api
@pytest.mark.asyncio
async def test_live_openalex_smoke():
    if not _live_api_integration_enabled():
        pytest.skip("set LIVE_API_AGENTS_INTEGRATION=1")
    from agents.openalex_agent import openalex_agent

    await _smoke_search("openalex", openalex_agent.search("machine learning medicine", max_results=3), 45.0)


@pytest.mark.live_api
@pytest.mark.asyncio
async def test_live_crossref_smoke():
    if not _live_api_integration_enabled():
        pytest.skip("set LIVE_API_AGENTS_INTEGRATION=1")
    from agents.crossref_agent import crossref_agent

    await _smoke_search("crossref", crossref_agent.search("clinical trial oncology", max_results=3), 45.0)


@pytest.mark.live_api
@pytest.mark.asyncio
async def test_live_ror_smoke():
    if not _live_api_integration_enabled():
        pytest.skip("set LIVE_API_AGENTS_INTEGRATION=1")
    from agents.ror_agent import ror_agent

    await _smoke_search("ror", ror_agent.search("Mayo Clinic", max_results=3), 35.0)


@pytest.mark.live_api
@pytest.mark.asyncio
async def test_live_npi_registry_smoke():
    if not _live_api_integration_enabled():
        pytest.skip("set LIVE_API_AGENTS_INTEGRATION=1")
    from agents.npi_registry_agent import npi_registry_agent

    await _smoke_search(
        "npi_registry", npi_registry_agent.search("Mayo Clinic", max_results=3), 40.0
    )


@pytest.mark.live_api
@pytest.mark.asyncio
async def test_live_nih_reporter_smoke():
    if not _live_api_integration_enabled():
        pytest.skip("set LIVE_API_AGENTS_INTEGRATION=1")
    from agents.nih_reporter_agent import nih_reporter_agent

    await _smoke_search(
        "nih_reporter", nih_reporter_agent.search("cancer immunotherapy", max_results=3), 90.0
    )


@pytest.mark.live_api
@pytest.mark.asyncio
async def test_live_open_payments_smoke():
    if not _live_api_integration_enabled():
        pytest.skip("set LIVE_API_AGENTS_INTEGRATION=1")
    from agents.open_payments_agent import open_payments_agent

    await _smoke_search(
        "open_payments", open_payments_agent.search("general payment physician", max_results=5), 60.0
    )


@pytest.mark.live_api
@pytest.mark.asyncio
async def test_live_eu_ctis_smoke():
    if not _live_api_integration_enabled():
        pytest.skip("set LIVE_API_AGENTS_INTEGRATION=1")
    from agents.eu_ctis_agent import eu_ctis_agent

    await _smoke_search("eu_ctis", eu_ctis_agent.search("oncology", max_results=3), 60.0)


@pytest.mark.live_api
@pytest.mark.asyncio
async def test_live_isrctn_smoke():
    if not _live_api_integration_enabled():
        pytest.skip("set LIVE_API_AGENTS_INTEGRATION=1")
    from agents.isrctn_agent import isrctn_agent

    await _smoke_search("isrctn", isrctn_agent.search("diabetes", max_results=3), 45.0)


@pytest.mark.live_api
@pytest.mark.asyncio
async def test_live_cms_open_data_smoke():
    if not _live_api_integration_enabled():
        pytest.skip("set LIVE_API_AGENTS_INTEGRATION=1")
    from agents.cms_open_data_agent import cms_open_data_agent

    await _smoke_search(
        "cms_open_data", cms_open_data_agent.search("hospital Maryland", max_results=5), 90.0
    )


@pytest.mark.live_api
@pytest.mark.asyncio
async def test_live_fda_datadashboard_smoke():
    if not _live_api_integration_enabled():
        pytest.skip("set LIVE_API_AGENTS_INTEGRATION=1")
    if not _fda_dd_configured():
        pytest.skip("set FDA_DATADASHBOARD_USER and FDA_DATADASHBOARD_KEY for live DDAPI test")
    from agents.fda_datadashboard_agent import fda_datadashboard_agent

    await _smoke_search(
        "fda_datadashboard",
        fda_datadashboard_agent.search("inspection food", max_results=5),
        90.0,
    )
