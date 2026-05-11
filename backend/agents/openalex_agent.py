"""OpenAlex — live works / literature metadata."""
from __future__ import annotations

import logging
from typing import Any, Dict, List
from urllib.parse import urlencode

import httpx

from config import settings
from models.schemas import LiveDataSearchResult
from utils.live_api_http import safe_json_preview, sanitize_free_text_query
from utils.logger import log_error
from utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


class OpenAlexAgent:
    def __init__(self) -> None:
        self._base = settings.OPENALEX_BASE_URL.rstrip("/")
        self._timeout = httpx.Timeout(30.0)

    async def search(self, query: str, max_results: int = 50) -> List[LiveDataSearchResult]:
        q = sanitize_free_text_query(query, 400)
        if not q:
            return []
        per = min(max(1, max_results), 200)
        params: Dict[str, Any] = {"search": q, "per_page": per, "page": 1}
        if settings.OPENALEX_API_KEY:
            params["api_key"] = settings.OPENALEX_API_KEY
        await rate_limiter.acquire("openalex")
        url = f"{self._base}/works?{urlencode(params)}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                r = await client.get(url)
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            log_error(e, "openalex search")
            return []

        out: List[LiveDataSearchResult] = []
        for w in (data.get("results") or [])[:per]:
            title = w.get("display_name") or w.get("title") or "Work"
            wid = w.get("id") or ""
            doi = (w.get("doi") or "").replace("https://doi.org/", "")
            url_best = wid
            if doi:
                url_best = f"https://doi.org/{doi}"
            meta = {
                "openalex_id": wid,
                "doi": doi,
                "publication_year": w.get("publication_year"),
                "type": w.get("type"),
            }
            out.append(
                LiveDataSearchResult(
                    url=url_best or "https://openalex.org",
                    title=str(title)[:500],
                    content=safe_json_preview(w, 10000),
                    source_domain="api.openalex.org",
                    metadata=meta,
                )
            )
        return out


openalex_agent = OpenAlexAgent()
