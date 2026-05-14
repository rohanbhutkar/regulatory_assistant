"""
Brave Web Search API helper (GET /res/v1/web/search).

Used when Google Custom Search returns HTTP 429 or as an explicit fallback.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional, Union

import httpx

from config import settings
from utils.logger import log_api_call, log_error, log_warning
from utils.rate_limiter import rate_limiter


def clip_brave_query(q: str) -> str:
    """Brave `q`: max 400 characters and 50 words (API limits)."""
    q = (q or "").strip()
    if not q:
        return q
    words = q.split()
    if len(words) > 50:
        q = " ".join(words[:50])
    if len(q) > 400:
        cut = q[:400].rsplit(" ", 1)[0].strip()
        q = cut if len(cut) > 24 else q[:400]
    return q


def urls_from_brave_payload(data: Dict[str, Any]) -> List[str]:
    urls: List[str] = []
    web = data.get("web") if isinstance(data, dict) else None
    if isinstance(web, dict):
        for item in web.get("results") or []:
            if isinstance(item, dict) and item.get("url"):
                urls.append(str(item["url"]))
    return urls


def _timeout_value(timeout: Union[httpx.Timeout, float]) -> httpx.Timeout:
    if isinstance(timeout, httpx.Timeout):
        return timeout
    return httpx.Timeout(float(timeout))


async def fetch_brave_web_urls(
    brave_variants: List[str],
    *,
    num_results: int,
    timeout: Union[httpx.Timeout, float],
    operators: bool = False,
) -> List[str]:
    """
    Call Brave Web Search for each variant until one returns web URLs.

    ``operators`` should be True when queries use ``site:`` (China CSE-style strings).
    """
    token = (settings.BRAVE_API_KEY or "").strip()
    if not token or not brave_variants:
        return []

    await rate_limiter.acquire("brave_search")
    base = (settings.BRAVE_WEB_SEARCH_URL or "https://api.search.brave.com/res/v1/web/search").strip()
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": token,
        "User-Agent": "Clinical-Knowledge-Agent/1.0",
    }
    count = max(1, min(20, int(num_results or 10)))
    to = _timeout_value(timeout)

    async with httpx.AsyncClient(timeout=to) as client:
        for q_try in brave_variants[:16]:
            if len(q_try) < 2:
                continue
            params: Dict[str, Any] = {
                "q": q_try,
                "count": count,
                "result_filter": "web",
                "safesearch": "off",
            }
            if operators:
                params["operators"] = "true"
            t0 = asyncio.get_event_loop().time()
            try:
                response = await client.get(base, params=params, headers=headers)
            except httpx.RequestError as e:
                log_error(e, "Brave web search request")
                continue
            sc = response.status_code
            elapsed = asyncio.get_event_loop().time() - t0
            if sc == 200:
                try:
                    data = response.json()
                except Exception as e:
                    log_error(e, "Brave web search JSON decode")
                    continue
                urls = urls_from_brave_payload(data)
                if urls:
                    log_api_call("brave_search", "brave_web_search", sc, elapsed)
                    return urls[:num_results]
                continue
            if sc == 429:
                log_warning(
                    f"Brave Web Search returned 429 (query len={len(q_try)}); trying next variant if any."
                )
                continue
            if sc in (502, 503):
                log_warning(f"Brave Web Search returned {sc}; trying next variant")
                continue
            log_warning(f"Brave Web Search HTTP {sc}: {response.text[:240]!r}")

    return []
