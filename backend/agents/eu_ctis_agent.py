"""EU CTIS public API — trial search (live)."""
from __future__ import annotations

import logging
from typing import Any, Dict, List

import httpx

from config import settings
from models.schemas import LiveDataSearchResult
from utils.live_api_http import safe_json_preview, sanitize_free_text_query
from utils.logger import log_error
from utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


class EuCtisAgent:
    def __init__(self) -> None:
        self._search = settings.EU_CTIS_SEARCH_URL
        self._retrieve_prefix = settings.EU_CTIS_RETRIEVE_PREFIX.rstrip("/")
        self._timeout = httpx.Timeout(45.0)

    async def search(self, query: str, max_results: int = 50) -> List[LiveDataSearchResult]:
        q = sanitize_free_text_query(query, 400)
        if not q:
            return []
        size = min(max(1, max_results), 50)
        body: Dict[str, Any] = {
            "pagination": {"page": 1, "size": size},
            "sort": {"property": "decisionDate", "direction": "DESC"},
            "searchCriteria": {
                "title": q,
            },
        }
        await rate_limiter.acquire("eu_ctis")
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.post(
                    self._search,
                    json=body,
                    headers={"Content-Type": "application/json"},
                )
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            log_error(e, "eu_ctis search")
            return []

        rows = data.get("data") or data.get("results") or []
        out: List[LiveDataSearchResult] = []
        for row in rows[:size]:
            ct = row.get("ctNumber") or row.get("ct_number") or ""
            title = row.get("ctTitle") or row.get("title") or f"Trial {ct}"
            url = f"{self._retrieve_prefix}/{ct}" if ct else "https://euclinicaltrials.eu/"
            out.append(
                LiveDataSearchResult(
                    url=url,
                    title=str(title)[:500],
                    content=safe_json_preview(row, 10000),
                    source_domain="euclinicaltrials.eu",
                    metadata={"ct_number": ct, "sponsor": row.get("sponsor")},
                )
            )
        return out


eu_ctis_agent = EuCtisAgent()
