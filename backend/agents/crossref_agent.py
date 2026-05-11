"""Crossref REST API — DOI / work metadata search."""
from __future__ import annotations

import logging
from typing import List
from urllib.parse import urlencode

import httpx

from config import settings
from models.schemas import LiveDataSearchResult
from utils.live_api_http import safe_json_preview, sanitize_free_text_query
from utils.logger import log_error
from utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


class CrossrefAgent:
    def __init__(self) -> None:
        self._base = settings.CROSSREF_BASE_URL.rstrip("/")
        self._mailto = settings.CROSSREF_MAILTO or "study-designer@localhost"
        self._timeout = httpx.Timeout(30.0)

    async def search(self, query: str, max_results: int = 50) -> List[LiveDataSearchResult]:
        q = sanitize_free_text_query(query, 400)
        if not q:
            return []
        rows = min(max(1, max_results), 100)
        params = {
            "query": q,
            "rows": rows,
            "mailto": self._mailto,
        }
        await rate_limiter.acquire("crossref")
        url = f"{self._base}/works?{urlencode(params)}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.get(url)
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            log_error(e, "crossref search")
            return []

        items = (data.get("message") or {}).get("items") or []
        out: List[LiveDataSearchResult] = []
        for it in items[:rows]:
            title_list = it.get("title") or []
            title = title_list[0] if title_list else "Crossref work"
            doi = it.get("DOI") or ""
            url_best = f"https://doi.org/{doi}" if doi else self._base
            out.append(
                LiveDataSearchResult(
                    url=url_best,
                    title=str(title)[:500],
                    content=safe_json_preview(it, 9000),
                    source_domain="api.crossref.org",
                    metadata={"doi": doi, "type": it.get("type")},
                )
            )
        return out


crossref_agent = CrossrefAgent()
