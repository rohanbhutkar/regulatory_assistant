"""FDA Data Dashboard API — inspections / import refusals (live; requires credentials)."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

import httpx

from config import settings
from models.schemas import LiveDataSearchResult
from utils.live_api_http import safe_json_preview, sanitize_free_text_query
from utils.logger import log_error
from utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


class FdaDatadashboardAgent:
    def __init__(self) -> None:
        self._base = settings.FDA_DATADASHBOARD_BASE_URL.rstrip("/")
        self._user = settings.FDA_DATADASHBOARD_USER
        self._key = settings.FDA_DATADASHBOARD_KEY
        self._timeout = httpx.Timeout(45.0)

    def _headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization-User": self._user,
            "Authorization-Key": self._key,
        }

    def _endpoint(self, query: str) -> str:
        q = query.lower()
        if "import" in q or "refusal" in q or "port" in q:
            return f"{self._base}/import_refusals"
        return f"{self._base}/inspections"

    async def search(self, query: str, max_results: int = 50) -> List[LiveDataSearchResult]:
        q = sanitize_free_text_query(query, 300)
        if not self._user or not self._key:
            return [
                LiveDataSearchResult(
                    url="https://datadashboard.fda.gov/",
                    title="FDA Data Dashboard — credentials required",
                    content=(
                        "Set FDA_DATADASHBOARD_USER and FDA_DATADASHBOARD_KEY in the environment "
                        "(see FDA OII unified logon). All DDAPI calls use POST with JSON body."
                    ),
                    source_domain="api-datadashboard.fda.gov",
                )
            ]
        if not q:
            return []

        await rate_limiter.acquire("fda_datadashboard")
        ep = self._endpoint(q)
        rows_cap = min(max(1, max_results), 200)
        sort_field = "InspectionEndDate" if "inspection" in ep else "RefusalDate"
        body: Dict[str, Any] = {
            "start": 1,
            "rows": rows_cap,
            "sort": sort_field,
            "sortorder": "DESC",
            "filters": {},
            "columns": [],
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.post(ep, json=body, headers=self._headers())
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            log_error(e, "fda_datadashboard")
            return [
                LiveDataSearchResult(
                    url="https://datadashboard.fda.gov/",
                    title="FDA Data Dashboard request failed",
                    content=str(e),
                    source_domain="api-datadashboard.fda.gov",
                )
            ]

        if data.get("statuscode") not in (400, 200):
            return [
                LiveDataSearchResult(
                    url="https://datadashboard.fda.gov/",
                    title="FDA Data Dashboard — unexpected status",
                    content=safe_json_preview(data, 4000),
                    source_domain="api-datadashboard.fda.gov",
                )
            ]

        results = data.get("result") or []
        q_low = q.lower()
        out: List[LiveDataSearchResult] = []
        for row in results:
            if len(out) >= max_results:
                break
            if not isinstance(row, dict):
                continue
            blob = json.dumps(row, default=str).lower()
            if q_low and q_low not in blob:
                continue
            name = row.get("LegalName") or row.get("FirmName") or row.get("FEINumber") or "FDA record"
            iid = row.get("InspectionID") or row.get("FEINumber") or ""
            out.append(
                LiveDataSearchResult(
                    url="https://datadashboard.fda.gov/",
                    title=str(name)[:500],
                    content=safe_json_preview(row, 10000),
                    source_domain="api-datadashboard.fda.gov",
                    metadata={"id": str(iid)},
                )
            )
        return out


fda_datadashboard_agent = FdaDatadashboardAgent()
