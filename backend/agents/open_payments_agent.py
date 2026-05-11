"""CMS Open Payments — metastore dataset discovery + optional datastore query."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

import httpx

from config import settings
from models.schemas import LiveDataSearchResult
from utils.live_api_http import safe_json_preview, sanitize_free_text_query, truncate_text
from utils.logger import log_error
from utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


class OpenPaymentsAgent:
    def __init__(self) -> None:
        self._base = settings.OPEN_PAYMENTS_BASE_URL.rstrip("/")
        self._timeout = httpx.Timeout(45.0)
        self._resource_ids = [
            x.strip()
            for x in (settings.OPEN_PAYMENTS_DATASTORE_RESOURCE_IDS or "").split(",")
            if x.strip()
        ]

    async def search(self, query: str, max_results: int = 50) -> List[LiveDataSearchResult]:
        q_low = sanitize_free_text_query(query, 300).lower()
        q_raw = sanitize_free_text_query(query, 300)
        await rate_limiter.acquire("open_payments")
        out: List[LiveDataSearchResult] = []

        meta_url = f"{self._base}/api/1/metastore/schemas/dataset/items"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.get(meta_url)
                r.raise_for_status()
                datasets = r.json()
        except Exception as e:
            log_error(e, "open_payments metastore")
            return [
                LiveDataSearchResult(
                    url="https://openpaymentsdata.cms.gov/",
                    title="Open Payments API unavailable",
                    content=str(e),
                    source_domain="openpaymentsdata.cms.gov",
                )
            ]

        if not isinstance(datasets, list):
            datasets = []

        max_catalog = 25
        catalog_n = 0
        for ds in datasets:
            if len(out) >= max_results:
                break
            title = str(ds.get("title") or ds.get("name") or "")
            desc = str(ds.get("description") or "")
            blob = f"{title} {desc}".lower()
            if q_raw:
                if q_low not in blob and not any(
                    t in blob for t in q_low.split() if len(t) > 3
                ):
                    continue
            else:
                if catalog_n >= max_catalog:
                    break
            did = ds.get("identifier") or ds.get("id") or ""
            out.append(
                LiveDataSearchResult(
                    url=f"https://openpaymentsdata.cms.gov/dataset/{did}",
                    title=title[:500] or "Open Payments dataset",
                    content=truncate_text(desc or safe_json_preview(ds, 4000), 12000),
                    source_domain="openpaymentsdata.cms.gov",
                    metadata={"dataset_identifier": did},
                )
            )
            if not q_raw:
                catalog_n += 1

        if self._resource_ids and q_raw:
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    body: Dict[str, Any] = {
                        "resources": [{"id": rid, "alias": f"t{i}"} for i, rid in enumerate(self._resource_ids[:3])],
                        "limit": min(max_results, 50),
                        "offset": 0,
                    }
                    r = await client.post(
                        f"{self._base}/api/1/datastore/query",
                        json=body,
                        headers={"Content-Type": "application/json"},
                    )
                    if r.status_code == 200:
                        dq = r.json()
                        for i, row in enumerate((dq.get("results") or [])[:max_results]):
                            out.append(
                                LiveDataSearchResult(
                                    url="https://openpaymentsdata.cms.gov/",
                                    title=f"Payment row {i + 1}",
                                    content=truncate_text(json.dumps(row, default=str), 10000),
                                    source_domain="openpaymentsdata.cms.gov",
                                    metadata={"row": row},
                                )
                            )
            except Exception as e:
                logger.debug("open_payments datastore optional query failed: %s", e)

        if not out and q_raw:
            out.append(
                LiveDataSearchResult(
                    url="https://openpaymentsdata.cms.gov/",
                    title="Open Payments — no dataset title match",
                    content=(
                        "No datasets matched the query text in the metastore catalog. "
                        "Try broader keywords or set OPEN_PAYMENTS_DATASTORE_RESOURCE_IDS for raw datastore queries."
                    ),
                    source_domain="openpaymentsdata.cms.gov",
                )
            )
        return out[:max_results]


open_payments_agent = OpenPaymentsAgent()
