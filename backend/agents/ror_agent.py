"""ROR API v2 — research organization lookup."""
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


class RorAgent:
    def __init__(self) -> None:
        self._base = settings.ROR_API_BASE_URL.rstrip("/")
        self._timeout = httpx.Timeout(25.0)

    async def search(self, query: str, max_results: int = 50) -> List[LiveDataSearchResult]:
        q = sanitize_free_text_query(query, 300)
        if not q:
            return []
        await rate_limiter.acquire("ror")
        url = f"{self._base}/v2/organizations?{urlencode({'query': q})}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.get(url)
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            log_error(e, "ror search")
            return []

        items = data.get("items") or []
        out: List[LiveDataSearchResult] = []
        for org in items[: max(1, max_results)]:
            rid = org.get("id") or ""
            name = org.get("name") or "Organization"
            loc0 = (org.get("locations") or [{}])[0]
            country = ""
            if isinstance(loc0, dict):
                gd = loc0.get("geonames_details")
                if isinstance(gd, dict):
                    country = str(gd.get("country_name") or "")
                if not country:
                    country = str(loc0.get("country_code") or "")
            out.append(
                LiveDataSearchResult(
                    url=rid or "https://ror.org",
                    title=str(name)[:500],
                    content=safe_json_preview(org, 8000),
                    source_domain="api.ror.org",
                    metadata={"ror_id": rid, "country": country},
                )
            )
        return out


ror_agent = RorAgent()
