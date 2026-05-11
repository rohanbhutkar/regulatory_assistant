"""ISRCTN public API — trial query (WHO XML format; registry returns XML, not JSON)."""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import List
from urllib.parse import quote, urlencode

import httpx

from config import settings
from models.schemas import LiveDataSearchResult
from utils.live_api_http import sanitize_free_text_query, truncate_text
from utils.logger import log_error
from utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


def _parse_who_xml(body: str, base_url: str, limit: int) -> List[LiveDataSearchResult]:
    root = ET.fromstring(body)
    out: List[LiveDataSearchResult] = []
    for trial in root.iter("trial"):
        if len(out) >= limit:
            break
        main = trial.find("main")
        if main is None:
            continue

        def _txt(tag: str) -> str:
            el = main.find(tag)
            return (el.text or "").strip() if el is not None else ""

        trial_id = _txt("trial_id")
        title = _txt("public_title") or _txt("scientific_title") or trial_id or "ISRCTN trial"
        page_url = _txt("url")
        if not page_url and trial_id:
            slug = trial_id.replace("ISRCTN", "").strip() or trial_id
            page_url = f"{base_url.rstrip('/')}/ISRCTN{quote(slug)}"
        if not page_url:
            page_url = base_url

        meta = {
            "trial_id": trial_id,
            "primary_sponsor": _txt("primary_sponsor"),
            "recruitment_status": _txt("recruitment_status"),
            "phase": _txt("phase"),
        }
        snippet_parts = [f"{k}: {v}" for k, v in meta.items() if v]
        content = truncate_text("\n".join(snippet_parts), 10000)

        out.append(
            LiveDataSearchResult(
                url=page_url,
                title=str(title)[:500],
                content=content,
                source_domain="www.isrctn.com",
                metadata=meta,
            )
        )
    return out


class IsrctnAgent:
    def __init__(self) -> None:
        self._base = settings.ISRCTN_API_BASE_URL.rstrip("/")
        self._timeout = httpx.Timeout(35.0)

    async def search(self, query: str, max_results: int = 50) -> List[LiveDataSearchResult]:
        q = sanitize_free_text_query(query, 500)
        if not q:
            return []
        limit = min(max(1, max_results), 100)
        params = {"q": q, "limit": limit}
        # WHO format returns structured XML (default format is also XML, not JSON).
        path = f"/api/query/format/who?{urlencode(params)}"
        await rate_limiter.acquire("isrctn")
        url = f"{self._base}{path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                r = await client.get(url)
                r.raise_for_status()
                text = r.text or ""
        except Exception as e:
            log_error(e, "isrctn search")
            return []

        if not text.strip().startswith("<"):
            logger.warning("isrctn: unexpected non-XML response")
            return []

        try:
            return _parse_who_xml(text, self._base, limit)
        except ET.ParseError as e:
            log_error(e, "isrctn xml parse")
            return []


isrctn_agent = IsrctnAgent()
