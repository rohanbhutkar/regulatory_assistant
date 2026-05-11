"""CMS NPI Registry — live provider / organization lookup."""
from __future__ import annotations

import logging
import re
from typing import List
from urllib.parse import urlencode

import httpx

from config import settings
from models.schemas import LiveDataSearchResult
from utils.live_api_http import sanitize_free_text_query, truncate_text
from utils.logger import log_error
from utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


def _params_for_query(query: str) -> dict:
    q = sanitize_free_text_query(query, 200)
    base = {"version": "2.1", "limit": "200"}
    digits = re.sub(r"\D", "", q)
    if len(digits) == 10:
        return {**base, "number": digits}
    if re.search(r"\b(org|organization|hospital|center|centre|university|clinic)\b", q, re.I):
        return {**base, "organization_name": q[:80]}
    parts = q.split()
    if len(parts) >= 2:
        return {**base, "first_name": parts[0][:40], "last_name": " ".join(parts[1:])[:40]}
    if len(q) >= 2:
        return {**base, "last_name": q[:60]}
    return {**base, "organization_name": q or "a*"}


class NpiRegistryAgent:
    def __init__(self) -> None:
        self._base = f"{settings.NPI_REGISTRY_BASE_URL.rstrip('/')}/"
        self._timeout = httpx.Timeout(30.0)

    async def search(self, query: str, max_results: int = 50) -> List[LiveDataSearchResult]:
        q = sanitize_free_text_query(query, 200)
        if not q:
            return []
        params = _params_for_query(q)
        await rate_limiter.acquire("npi_registry")
        url = f"{self._base}?{urlencode(params)}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.get(url)
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            log_error(e, "npi_registry search")
            return []

        errs = data.get("Errors")
        if errs:
            logger.info("NPI registry errors: %s", errs)
            return []

        out: List[LiveDataSearchResult] = []
        for row in data.get("results") or []:
            if len(out) >= max_results:
                break
            num = row.get("number", "")
            basic = row.get("basic") or {}
            et = row.get("enumeration_type", "")
            if et == "NPI-2":
                title = basic.get("organization_name") or f"Organization NPI {num}"
            else:
                title = (
                    f"{basic.get('first_name', '')} {basic.get('last_name', '')}".strip()
                    or f"Provider NPI {num}"
                )
            addrs = row.get("addresses") or []
            loc = addrs[0] if addrs else {}
            city = loc.get("city", "")
            state = loc.get("state", "")
            line1 = loc.get("address_1", "")
            content = truncate_text(
                f"NPI: {num}\nType: {et}\n{line1}\n{city}, {state}\n"
                + str(basic)[:4000],
                8000,
            )
            out.append(
                LiveDataSearchResult(
                    url=f"https://npiregistry.cms.hhs.gov/provider-view/{num}",
                    title=title[:500],
                    content=content,
                    source_domain="npiregistry.cms.hhs.gov",
                    metadata={"npi": num, "enumeration_type": et},
                )
            )
        return out


npi_registry_agent = NpiRegistryAgent()
