"""NIH RePORTER API v2 — live projects search (no local DB)."""
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


class NihReporterAgent:
    def __init__(self) -> None:
        self._url = f"{settings.NIH_REPORTER_BASE_URL.rstrip('/')}/v2/projects/search"
        self._timeout = httpx.Timeout(45.0)

    async def search(self, query: str, max_results: int = 50) -> List[LiveDataSearchResult]:
        q = sanitize_free_text_query(query, 500)
        if not q:
            return []
        await rate_limiter.acquire("nih_reporter")
        body: Dict[str, Any] = {
            "criteria": {
                "use_relevance": True,
                "advanced_text_search": {
                    "operator": "and",
                    "search_field": "projecttitle,terms,abstracttext",
                    "search_text": q,
                },
            },
            "offset": 0,
            "limit": min(max(1, max_results), 500),
            "sort_field": "fiscal_year",
            "sort_order": "desc",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.post(
                    self._url,
                    json=body,
                    headers={"Content-Type": "application/json"},
                )
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            log_error(e, "nih_reporter search")
            logger.warning("NIH Reporter request failed: %s", e)
            return []

        hits: List[LiveDataSearchResult] = []
        for row in data.get("results") or data.get("data") or []:
            if len(hits) >= max_results:
                break
            proj = row.get("project") if isinstance(row.get("project"), dict) else row
            title = (
                proj.get("project_title")
                or proj.get("title")
                or proj.get("projectTitle")
                or "NIH project"
            )
            core = proj.get("core_project_num") or proj.get("project_num") or ""
            org = proj.get("organization") if isinstance(proj.get("organization"), dict) else {}
            org_name = org.get("org_name") or org.get("organization_name") or ""
            url = proj.get("project_detail_url") or proj.get("url") or ""
            if not url and core:
                url = f"https://reporter.nih.gov/search/{str(core).replace(' ', '')}/details"
            meta = {
                "core_project_num": core,
                "organization": org_name,
                "fiscal_year": proj.get("fiscal_year"),
                "award_amount": proj.get("award_amount"),
            }
            content = safe_json_preview({k: v for k, v in meta.items() if v}, 6000)
            hits.append(
                LiveDataSearchResult(
                    url=url or "https://reporter.nih.gov/",
                    title=str(title)[:500],
                    content=content,
                    source_domain="api.reporter.nih.gov",
                    relevance_score=None,
                    metadata=meta,
                )
            )
        return hits


nih_reporter_agent = NihReporterAgent()
