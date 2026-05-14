"""Brave Web Search fallback when Google CSE returns 429 (google_search agent)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.fierce_pharma_agent import GoogleSearchAgent
from utils.brave_web_search import clip_brave_query, urls_from_brave_payload


def test_clip_brave_query_word_and_char_limits() -> None:
    long = "word " * 60
    out = clip_brave_query(long)
    assert len(out.split()) <= 50
    assert len(out) <= 400


def test_urls_from_brave_payload() -> None:
    data = {
        "web": {
            "results": [
                {"url": "https://example.com/a", "title": "A"},
                {"url": "https://example.com/b"},
            ]
        }
    }
    assert urls_from_brave_payload(data) == [
        "https://example.com/a",
        "https://example.com/b",
    ]


@pytest.mark.asyncio
async def test_brave_fallback_on_google_429(monkeypatch) -> None:
    from config import settings

    monkeypatch.setattr(settings, "GOOGLE_API_KEY", "gk")
    monkeypatch.setattr(settings, "GOOGLE_SEARCH_ENGINE_ID", "cx")
    monkeypatch.setattr(settings, "BRAVE_API_KEY", "bk")

    r429 = MagicMock()
    r429.status_code = 429

    agent = GoogleSearchAgent()
    agent.base_url = "https://www.googleapis.com/customsearch/v1"

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get = AsyncMock(side_effect=[r429])

    with patch("agents.fierce_pharma_agent._llm_expand_cse_queries", new_callable=AsyncMock, return_value=[]):
        with patch("agents.fierce_pharma_agent.httpx.AsyncClient", return_value=mock_client):
            with patch.object(agent, "_brave_search_urls", new_callable=AsyncMock) as brave_mock:
                brave_mock.return_value = ["https://news.example/x"]
                urls = await agent._make_google_search("some drug trial", 5)

    assert urls == ["https://news.example/x"]
    brave_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_google_429_brave_empty_then_google_after_backoff(monkeypatch) -> None:
    from config import settings

    monkeypatch.setattr(settings, "GOOGLE_API_KEY", "gk")
    monkeypatch.setattr(settings, "GOOGLE_SEARCH_ENGINE_ID", "cx")
    monkeypatch.setattr(settings, "BRAVE_API_KEY", "bk")
    monkeypatch.setattr(settings, "GOOGLE_SEARCH_CSE_429_BACKOFF_ROUNDS", 2)

    r429 = MagicMock()
    r429.status_code = 429
    r200 = MagicMock()
    r200.status_code = 200
    r200.json = MagicMock(
        return_value={"items": [{"link": "https://example.com/after-retry"}]}
    )

    agent = GoogleSearchAgent()
    agent.base_url = "https://www.googleapis.com/customsearch/v1"

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get = AsyncMock(side_effect=[r429, r200])

    sleep_mock = AsyncMock()
    monkeypatch.setattr("agents.fierce_pharma_agent.asyncio.sleep", sleep_mock)

    with patch("agents.fierce_pharma_agent._llm_expand_cse_queries", new_callable=AsyncMock, return_value=[]):
        with patch("agents.fierce_pharma_agent.httpx.AsyncClient", return_value=mock_client):
            with patch.object(agent, "_brave_search_urls", new_callable=AsyncMock) as brave_mock:
                brave_mock.return_value = []
                urls = await agent._make_google_search("some drug trial", 5)

    assert urls == ["https://example.com/after-retry"]
    assert brave_mock.await_count == 1
    assert mock_client.get.call_count == 2
    assert sleep_mock.await_count == 1
@pytest.mark.asyncio
async def test_brave_search_urls_parses_web_results(monkeypatch) -> None:
    from config import settings

    monkeypatch.setattr(settings, "BRAVE_API_KEY", "secret")
    monkeypatch.setattr(settings, "BRAVE_WEB_SEARCH_URL", "https://api.search.brave.com/res/v1/web/search")

    ok = MagicMock()
    ok.status_code = 200
    ok.json = MagicMock(
        return_value={"web": {"results": [{"url": "https://a.test/1", "title": "t"}]}}
    )

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get = AsyncMock(return_value=ok)

    agent = GoogleSearchAgent()
    with patch("utils.brave_web_search.httpx.AsyncClient", return_value=mock_client):
        with patch("utils.brave_web_search.rate_limiter.acquire", new_callable=AsyncMock):
            urls = await agent._brave_search_urls(["query one"], 3)

    assert urls == ["https://a.test/1"]
    mock_client.get.assert_awaited_once()
    call_kw = mock_client.get.await_args
    assert "X-Subscription-Token" in (call_kw.kwargs.get("headers") or call_kw[1].get("headers", {}))
