"""
Unit tests for china_regulatory_agent (mocked httpx; no network).
Run from backend: pytest test_china_regulatory_agent.py -q
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.china_regulatory_agent import (
    ChinaRegulatoryAgent,
    _build_cse_query,
    _classify_portal,
    _expand_query_variations,
    _merge_url_batches,
    _rank_urls_by_quality,
    _relevance_score,
    _stem_instructions,
    _terms_for_relevance,
)


def test_classify_portal() -> None:
    assert _classify_portal("https://www.cde.org.cn/foo") == "cde"
    assert _classify_portal("https://zwfw.nmpa.gov.cn/x") == "zwfw"
    assert _classify_portal("https://www.nmpa.gov.cn/y") == "nmpa_root"


def test_build_cse_query_no_site_operators(monkeypatch) -> None:
    from config import settings

    monkeypatch.setattr(settings, "GOOGLE_CSE_CHINA_ENGINE_ID", "")
    q = _build_cse_query("抗肿瘤 指导原则", "recent")
    assert "site:" not in q.lower()
    assert "抗肿瘤" in q
    assert "recent" in q


def test_expand_query_variations_multiple_angles() -> None:
    v = _expand_query_variations("oncology drug approval China", None, 5)
    assert len(v) >= 3
    assert v[0] == "oncology drug approval China"
    assert any("药审中心" in x for x in v) or any("国家药监局" in x for x in v)


def test_merge_url_batches_dedupes_preserves_order() -> None:
    m = _merge_url_batches(
        [
            ["https://a/1", "https://b/2"],
            ["https://a/1", "https://c/3"],
        ]
    )
    assert m == ["https://a/1", "https://b/2", "https://c/3"]


def test_rank_urls_dedupes_preserves_order() -> None:
    urls = [
        "https://www.cde.org.cn/",
        "https://www.cde.org.cn/main/news/viewInfoCommon/abc123",
        "https://www.cde.org.cn/",
    ]
    ranked = _rank_urls_by_quality(urls)
    assert ranked == [
        "https://www.cde.org.cn/",
        "https://www.cde.org.cn/main/news/viewInfoCommon/abc123",
    ]


def test_terms_for_relevance_includes_cjk() -> None:
    t = _terms_for_relevance("糖尿病 化学药品 指导原则")
    assert any("指导原则" in x for x in t)
    assert any("化学药品" in x for x in t)


def test_relevance_score_uses_cjk_phrases() -> None:
    content = "本品适用于慢性鼻窦炎伴鼻息肉治疗药物临床试验技术指导原则正文说明"
    blob = "慢性鼻窦炎 鼻息肉 指导原则"
    score = _relevance_score(content, blob)
    assert score > 0.25


def test_stem_instructions_secondary_variation_gets_tail() -> None:
    ins = "只要CDE正式通告 不要首页"
    s0 = _stem_instructions("抗肿瘤", 0, ins)
    s1 = _stem_instructions("抗肿瘤 药审中心", 1, ins)
    assert s0 is not None and len(s0) >= 6
    assert s1 is not None


def test_build_cse_query_with_china_engine_id_same_plain_q(monkeypatch) -> None:
    from config import settings

    monkeypatch.setattr(settings, "GOOGLE_CSE_CHINA_ENGINE_ID", "abc123")
    q = _build_cse_query("抗肿瘤 指导原则", None)
    assert "site:" not in q.lower()
    assert "抗肿瘤" in q


def test_rank_urls_preserves_first_seen_order() -> None:
    mixed = [
        "https://fda.gov/a",
        "https://www.cde.org.cn/main/x",
        "https://news.example.com/cn",
        "https://www.gov.cn/foo",
        "https://www.nmpa.gov.cn/y",
    ]
    assert _rank_urls_by_quality(mixed) == mixed


@pytest.mark.asyncio
async def test_cse_urls_retries_on_503(monkeypatch) -> None:
    from config import settings

    monkeypatch.setattr(settings, "GOOGLE_API_KEY", "k")
    monkeypatch.setattr(settings, "GOOGLE_SEARCH_ENGINE_ID", "cx")
    monkeypatch.setattr(settings, "GOOGLE_CSE_CHINA_ENGINE_ID", "")
    monkeypatch.setattr(settings, "CHINA_REGULATORY_CSE_MAX_RETRIES", 5)
    monkeypatch.setattr(settings, "BRAVE_API_KEY", "")

    r503 = MagicMock()
    r503.status_code = 503
    r200 = MagicMock()
    r200.status_code = 200
    r200.raise_for_status = MagicMock()
    r200.json = MagicMock(return_value={"items": [{"link": "https://www.cde.org.cn/x"}]})

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get = AsyncMock(side_effect=[r503, r503, r200])

    sleep_mock = AsyncMock()
    monkeypatch.setattr("agents.china_regulatory_agent.asyncio.sleep", sleep_mock)

    agent = ChinaRegulatoryAgent()
    with patch("agents.china_regulatory_agent.httpx.AsyncClient", return_value=mock_client):
        with patch("agents.china_regulatory_agent.rate_limiter.acquire", new_callable=AsyncMock):
            urls = await agent._cse_urls("test q", 5)

    assert urls == ["https://www.cde.org.cn/x"]
    assert mock_client.get.call_count == 3
    assert sleep_mock.await_count == 2


@pytest.mark.asyncio
async def test_cse_urls_429_returns_brave_urls(monkeypatch) -> None:
    from config import settings

    monkeypatch.setattr(settings, "GOOGLE_API_KEY", "k")
    monkeypatch.setattr(settings, "GOOGLE_SEARCH_ENGINE_ID", "cx")
    monkeypatch.setattr(settings, "GOOGLE_CSE_CHINA_ENGINE_ID", "")
    monkeypatch.setattr(settings, "CHINA_REGULATORY_CSE_MAX_RETRIES", 3)
    monkeypatch.setattr(settings, "BRAVE_API_KEY", "bk")

    r429 = MagicMock()
    r429.status_code = 429

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get = AsyncMock(return_value=r429)

    sleep_mock = AsyncMock()
    monkeypatch.setattr("agents.china_regulatory_agent.asyncio.sleep", sleep_mock)

    agent = ChinaRegulatoryAgent()
    with patch("agents.china_regulatory_agent.httpx.AsyncClient", return_value=mock_client):
        with patch("agents.china_regulatory_agent.rate_limiter.acquire", new_callable=AsyncMock):
            with patch.object(
                agent,
                "_try_brave_cse_fallback",
                new_callable=AsyncMock,
                return_value=["https://www.cde.org.cn/from-brave"],
            ) as brave_mock:
                urls = await agent._cse_urls("test q", 5)

    assert urls == ["https://www.cde.org.cn/from-brave"]
    assert brave_mock.await_count >= 1
    assert mock_client.get.call_count == 1


@pytest.mark.asyncio
async def test_cse_urls_429_brave_empty_then_google_after_backoff(monkeypatch) -> None:
    """429 → Brave empty → backoff → retry Google and succeed."""
    from config import settings

    monkeypatch.setattr(settings, "GOOGLE_API_KEY", "k")
    monkeypatch.setattr(settings, "GOOGLE_SEARCH_ENGINE_ID", "cx")
    monkeypatch.setattr(settings, "GOOGLE_CSE_CHINA_ENGINE_ID", "")
    monkeypatch.setattr(settings, "CHINA_REGULATORY_CSE_MAX_RETRIES", 3)
    monkeypatch.setattr(settings, "BRAVE_API_KEY", "bk")

    r429 = MagicMock()
    r429.status_code = 429
    r200 = MagicMock()
    r200.status_code = 200
    r200.raise_for_status = MagicMock()
    r200.json = MagicMock(return_value={"items": [{"link": "https://www.cde.org.cn/retry-ok"}]})

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get = AsyncMock(side_effect=[r429, r200])

    sleep_mock = AsyncMock()
    monkeypatch.setattr("agents.china_regulatory_agent.asyncio.sleep", sleep_mock)

    agent = ChinaRegulatoryAgent()
    with patch("agents.china_regulatory_agent.httpx.AsyncClient", return_value=mock_client):
        with patch("agents.china_regulatory_agent.rate_limiter.acquire", new_callable=AsyncMock):
            with patch.object(
                agent,
                "_try_brave_cse_fallback",
                new_callable=AsyncMock,
                return_value=[],
            ) as brave_mock:
                urls = await agent._cse_urls("test q", 5)

    assert urls == ["https://www.cde.org.cn/retry-ok"]
    assert brave_mock.await_count == 1
    assert mock_client.get.call_count == 2
    assert sleep_mock.await_count == 1
@pytest.mark.asyncio
async def test_search_regulatory_cse_and_fetch(monkeypatch) -> None:
    from config import settings

    monkeypatch.setattr(settings, "GOOGLE_API_KEY", "k")
    monkeypatch.setattr(settings, "GOOGLE_SEARCH_ENGINE_ID", "cx")
    monkeypatch.setattr(settings, "GOOGLE_CSE_CHINA_ENGINE_ID", "")
    monkeypatch.setattr(settings, "CHINA_REGULATORY_TRANSLATE_SNIPPETS", False)
    monkeypatch.setattr(settings, "CHINA_REGULATORY_QUERY_VARIATIONS_MAX", 1)
    monkeypatch.setattr(settings, "CHINA_REGULATORY_FETCH_CONCURRENCY", 1)

    cse_json = {"items": [{"link": "https://www.cde.org.cn/test/page.html"}]}
    html = (
        "<html><head><title>国家药监局药审中心 — 技术指导原则</title></head>"
        "<body><p>抗肿瘤药物临床试验技术指导原则 正文内容示例</p></body></html>"
    )

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    cse_resp = MagicMock()
    cse_resp.status_code = 200
    cse_resp.raise_for_status = MagicMock()
    cse_resp.json = MagicMock(return_value=cse_json)

    page_resp = MagicMock()
    page_resp.status_code = 200
    page_resp.raise_for_status = MagicMock()
    page_resp.headers = {"content-type": "text/html"}
    page_resp.text = html

    mock_client.get = AsyncMock(side_effect=[cse_resp, page_resp])

    with patch("agents.china_regulatory_agent.httpx.AsyncClient", return_value=mock_client):
        with patch("agents.china_regulatory_agent.cache_manager.get", return_value=None):
            with patch("agents.china_regulatory_agent.cache_manager.set") as mock_set:
                agent = ChinaRegulatoryAgent()
                out = await agent.search_regulatory("抗肿瘤 指导原则", "CDE", max_results=5)

    assert len(out) == 1
    assert out[0].url == "https://www.cde.org.cn/test/page.html"
    assert out[0].metadata.get("portal") == "cde"
    assert "技术指导" in out[0].content or "抗肿瘤" in out[0].content
    assert "药审中心" in out[0].title or "技术指导" in out[0].title

    cargs, ckwargs = mock_client.get.call_args_list[0]
    assert "customsearch" in str(cargs[0])
    params = ckwargs.get("params") or {}
    assert "site:" not in (params.get("q") or "").lower()
    assert "抗肿瘤" in params.get("q", "")

    mock_set.assert_called_once()


@pytest.mark.asyncio
async def test_translate_off_no_llm(monkeypatch) -> None:
    from config import settings

    monkeypatch.setattr(settings, "GOOGLE_API_KEY", "k")
    monkeypatch.setattr(settings, "GOOGLE_SEARCH_ENGINE_ID", "cx")
    monkeypatch.setattr(settings, "GOOGLE_CSE_CHINA_ENGINE_ID", "")
    monkeypatch.setattr(settings, "CHINA_REGULATORY_TRANSLATE_SNIPPETS", False)
    monkeypatch.setattr(settings, "CHINA_REGULATORY_QUERY_VARIATIONS_MAX", 1)
    monkeypatch.setattr(settings, "CHINA_REGULATORY_FETCH_CONCURRENCY", 1)

    cse_json = {"items": [{"link": "https://www.cde.org.cn/a.html"}]}
    html = (
        "<html><head><title>测试页面标题足够长用于提取</title></head>"
        "<body><p>抗肿瘤药物临床试验技术指导原则 正文内容足够长用于提取测试</p></body></html>"
    )

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    cse_resp = MagicMock()
    cse_resp.status_code = 200
    cse_resp.raise_for_status = MagicMock()
    cse_resp.json = MagicMock(return_value=cse_json)
    page_resp = MagicMock()
    page_resp.status_code = 200
    page_resp.raise_for_status = MagicMock()
    page_resp.headers = {"content-type": "text/html"}
    page_resp.text = html
    mock_client.get = AsyncMock(side_effect=[cse_resp, page_resp])

    with patch("agents.china_regulatory_agent.httpx.AsyncClient", return_value=mock_client):
        with patch("agents.china_regulatory_agent.cache_manager.get", return_value=None):
            with patch("agents.china_regulatory_agent.cache_manager.set"):
                with patch("agents.china_regulatory_agent.llm_agent.generate_response") as gen:
                    agent = ChinaRegulatoryAgent()
                    await agent.search_regulatory("test", None, max_results=3)
                    gen.assert_not_called()
