"""CMS data.cms.gov Data API v1 — hospital / FQHC enrollment style datasets (live)."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

import httpx

from config import settings
from models.schemas import LiveDataSearchResult
from utils.live_api_http import safe_json_preview, sanitize_free_text_query
from utils.logger import log_error
from utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

# From site-database reference: hospital enrollments + FQHC enrollments
_DATASETS: List[Tuple[str, str, str]] = [
    (
        "hospital_enrollments",
        "f6f6505c-e8b0-4d57-b258-e2b94133aaf2",
        "Hospital enrollments (Part A)",
    ),
    (
        "fqhc_enrollments",
        "4bcae866-3411-439a-b762-90a6187c194b",
        "FQHC enrollments",
    ),
]


class CmsOpenDataAgent:
    def __init__(self) -> None:
        self._base = settings.CMS_DATA_API_BASE_URL.rstrip("/")
        self._timeout = httpx.Timeout(40.0)

    def _pick_datasets(self, query: str) -> List[Tuple[str, str, str]]:
        q = query.lower()
        if any(k in q for k in ("fqhc", "federally qualified", "community health center", "health center")):
            return [d for d in _DATASETS if d[0] == "fqhc_enrollments"] or _DATASETS
        if any(k in q for k in ("hospital", "ccn", "acute", "inpatient", "medicare hospital")):
            return [d for d in _DATASETS if d[0] == "hospital_enrollments"] or _DATASETS
        return list(_DATASETS)

    async def search(self, query: str, max_results: int = 50) -> List[LiveDataSearchResult]:
        q_tokens = sanitize_free_text_query(query, 200).lower().split()
        await rate_limiter.acquire("cms_open_data")
        out: List[LiveDataSearchResult] = []
        size = min(100, max(10, max_results * 5))

        for key, ds_id, label in self._pick_datasets(query):
            if len(out) >= max_results:
                break
            url = f"{self._base}/data-api/v1/dataset/{ds_id}/data"
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    r = await client.get(url, params={"size": size, "offset": 0})
                    r.raise_for_status()
                    rows = r.json()
            except Exception as e:
                log_error(e, f"cms_open_data {key}")
                continue

            if not isinstance(rows, list):
                continue

            name_keys = (
                "ORGANIZATION NAME",
                "DOING BUSINESS AS NAME",
                "organization_name",
                "ORG_NAME",
            )
            city_keys = ("CITY", "city")
            state_keys = ("STATE", "state")
            npi_keys = ("NPI", "npi")

            for row in rows:
                if len(out) >= max_results:
                    break
                if not isinstance(row, dict):
                    continue
                blob = " ".join(str(v) for v in row.values() if v).lower()
                if q_tokens and not any(t in blob for t in q_tokens if len(t) > 2):
                    continue
                title = next(
                    (str(row[k]) for k in name_keys if row.get(k)),
                    label,
                )
                npi = next((str(row[k]) for k in npi_keys if row.get(k)), "")
                city = next((str(row[k]) for k in city_keys if row.get(k)), "")
                st = next((str(row[k]) for k in state_keys if row.get(k)), "")
                meta: Dict[str, Any] = {"dataset": key, "npi": npi, "city": city, "state": st}
                out.append(
                    LiveDataSearchResult(
                        url=f"https://data.cms.gov/provider-characteristics/hospitals-and-other-facilities",
                        title=f"{title[:400]} ({label})",
                        content=safe_json_preview(row, 8000),
                        source_domain="data.cms.gov",
                        metadata=meta,
                    )
                )
        if not out and q_tokens:
            out.append(
                LiveDataSearchResult(
                    url="https://data.cms.gov/",
                    title="CMS open data — no row matched",
                    content="Try organization name, city, state, NPI, or keywords like hospital or FQHC.",
                    source_domain="data.cms.gov",
                )
            )
        return out[:max_results]


cms_open_data_agent = CmsOpenDataAgent()
