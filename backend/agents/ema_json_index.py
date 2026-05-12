"""
EMA bulk JSON feeds (official twice-daily reports). Download, disk cache, local search.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from config import settings

logger = logging.getLogger(__name__)

# Relative to EMA_JSON_BASE_URL — see EMA "Download website data in JSON" page.
FEED_FILES: Dict[str, str] = {
    "medicines": "medicines-output-medicines_json-report_en.json",
    "post_authorisation": "medicines-output-post_authorisation_json-report_en.json",
    "epar_documents": "documents-output-epar_documents_json-report_en.json",
    "non_epar_documents": "documents-output-non_epar_documents_json-report_en.json",
    "all_documents": "documents-output-json-report_en.json",
    "guidance": "general-json-report_en.json",
    "orphan_designations": "medicines-output-orphan_designations-json-report_en.json",
    "shortages": "shortages-output-json-report_en.json",
    "referrals": "referrals-output-json-report_en.json",
    "dhpc": "dhpc-output-json-report_en.json",
    "psusa": "medicines-output-periodic_safety_update_report_single_assessments-output-json-report_en.json",
    "pip": "medicines-output-paediatric_investigation_plans-output-json-report_en.json",
}


def _default_cache_dir() -> Path:
    if settings.EMA_JSON_CACHE_DIR.strip():
        return Path(settings.EMA_JSON_CACHE_DIR)
    return Path(__file__).resolve().parent.parent / ".cache" / "ema_json"


def _runtime_cache_dir() -> Path:
    cache_root = os.getenv("XDG_CACHE_HOME", "").strip()
    if cache_root:
        return Path(cache_root) / "regulatory_bot" / "ema_json"
    return Path(tempfile.gettempdir()) / "regulatory_bot" / "ema_json"


def _norm(s: Any) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s).lower().strip())


# Generic regulatory / scope tokens — should not match rows by themselves (same idea as Google anchor vs generic pairs).
_REGULATORY_NOISE_TERMS: frozenset[str] = frozenset(
    {
        "prime",
        "designation",
        "designations",
        "epar",
        "epars",
        "assessment",
        "report",
        "reports",
        "smpc",
        "public",
        "european",
        "withdrawal",
        "refusal",
        "withdrawn",
        "variation",
        "variations",
        "authorisation",
        "authorization",
        "authorisations",
        "authorizations",
        "post",
        "pre",
        "marketing",
        "centralised",
        "centralized",
        "maa",
        "hma",
        "chmp",
        "committee",
        "scientific",
        "advice",
        "opinion",
        "opinions",
        "update",
        "updates",
        "extension",
        "label",
        "labeling",
        "labelling",
        "pipeline",
        "portfolio",
        "landscape",
        "overview",
        "survey",
        "status",
        "regulatory",
        "regulation",
        "medicine",
        "medicines",
        "drug",
        "drugs",
        "product",
        "products",
        "clinical",
        "trial",
        "trials",
        "study",
        "studies",
        "patient",
        "patients",
        "pediatric",
        "paediatric",
        "recent",
        "latest",
        "new",
        "news",
        "information",
        "data",
        "database",
        "search",
        "find",
        "list",
        "summary",
        "summarise",
        "summarize",
        "compare",
        "versus",
        "global",
        "multiple",
        "including",
        "related",
        "company",
        "companies",
        "sponsor",
        "sponsors",
        "pharmaceutical",
        "pharma",
        "eu",
        "ema",
        "union",
    }
)

# Long tokens that appear in many unrelated EMA rows (orphan maintenance, procedures, etc.).
# They must not be chosen as the sole "primary_long" gate in strict scoring — otherwise
# queries that also mention a company still match random sponsors' documents.
_PRIMARY_LONG_ANCHOR_BLOCKLIST: frozenset[str] = frozenset(
    {
        "maintenance",
        "designation",
        "designations",
        "combination",
        "combinations",
        "therapeutic",
        "investigation",
        "investigations",
        "application",
        "applications",
        "abbreviated",
        "supervision",
        "periodic",
        "population",
        "populations",
        "assessment",
        "assessments",
        "information",
        "communication",
        "procedure",
        "procedures",
        "extension",
        "extensions",
        "pediatric",
        "paediatric",
        "renewal",
        "renewals",
        "scientific",
        "submission",
        "submissions",
        "development",
        "medication",
        "medications",
        "treatment",
        "treatments",
        "withdrawal",
        "withdrawals",
    }
)


def _apply_company_terms_gate(
    score: float,
    company_terms: Optional[List[str]],
    identity_norm: str,
    blob_norm: str,
) -> float:
    """When the user named a MAH/sponsor, drop rows with no match in identity or row text."""
    if score <= 0 or not company_terms:
        return score
    gates = [t.strip().lower() for t in company_terms if len(t.strip()) >= 2][:8]
    if not gates:
        return score
    hay = f"{identity_norm} {blob_norm}".strip()
    if not any(g in hay for g in gates):
        return 0.0
    return score


def _density_score(blob: str, terms: List[str], inn: Optional[str]) -> float:
    """Average substring hit rate + INN bonus (legacy behaviour on the chosen term list)."""
    if not blob:
        return 0.0
    score = 0.0
    usable = [t.strip().lower() for t in terms if len(t.strip()) >= 2]
    for t in usable:
        if t in blob:
            score += 1.0
    if usable:
        score /= max(len(usable), 1)
    inn_l = (inn or "").strip().lower()
    if inn_l and inn_l in blob:
        score += 0.35
    return min(score, 2.0)


def augment_terms_from_query(query: str, routed: List[str], max_total: int = 14) -> List[str]:
    """Append anchor-like tokens from the raw query so long INNs / brands always affect scoring."""
    out: List[str] = []
    seen: set[str] = set()
    for t in routed:
        tl = str(t).strip().lower()
        if len(tl) < 2 or tl in seen:
            continue
        seen.add(tl)
        out.append(tl)
    for w in re.findall(r"[A-Za-z0-9][A-Za-z0-9\-%]{2,}", query or ""):
        wl = w.lower()
        if len(wl) < 3 or wl in _REGULATORY_NOISE_TERMS or wl in seen:
            continue
        seen.add(wl)
        out.append(wl)
        if len(out) >= max_total:
            break
    return out[:max_total]


def _anchor_terms(terms: List[str]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for t in terms:
        tl = t.strip().lower()
        if len(tl) < 3 or tl in _REGULATORY_NOISE_TERMS or tl in seen:
            continue
        seen.add(tl)
        out.append(tl)
    return out


def _score_row(
    blob: str,
    terms: List[str],
    inn: Optional[str],
    *,
    identity_blob: Optional[str] = None,
) -> float:
    """
    Score a row for EMA JSON search. When strict mode is on (default), generic regulatory tokens cannot
    match alone; medicine rows need an anchor (or INN) on identity fields. Long tokens (likely INNs) must
    hit identity when present — same discipline as entity-anchored Google queries.
    """
    if not blob:
        return 0.0

    if not settings.EMA_JSON_STRICT_ANCHOR_SCORING:
        return _density_score(blob, terms, inn)

    terms_f = [t.strip().lower() for t in terms if len(t.strip()) >= 2]
    if not terms_f:
        return 0.0

    anchors = _anchor_terms(terms_f)
    inn_l = (inn or "").strip().lower()
    gate_id = _norm(identity_blob) if identity_blob is not None else None
    blob_n = _norm(blob)
    inn_hit = bool(inn_l and inn_l in (gate_id or blob_n))

    min_long = max(6, int(getattr(settings, "EMA_JSON_LONG_ANCHOR_MIN_LEN", 9)))
    long_anchors = [a for a in anchors if len(a) >= min_long]
    must_surface = gate_id if gate_id is not None else blob_n
    # Prefer a discriminative long token (INN / brand / company), not generic procedure words
    # like "maintenance" that match many unrelated orphan/variation rows.
    if long_anchors and not inn_hit:
        strong_long = [a for a in long_anchors if a not in _PRIMARY_LONG_ANCHOR_BLOCKLIST]
        if strong_long:
            primary_long = max(strong_long, key=len)
            if primary_long not in must_surface:
                return 0.0

    if gate_id is not None:
        if not anchors and not inn_hit:
            return 0.0
        if anchors and not inn_hit and not any(a in gate_id for a in anchors):
            return 0.0
        if anchors:
            scoring_terms = anchors
        elif inn_hit:
            scoring_terms = [inn_l] if inn_l else terms_f
        else:
            scoring_terms = terms_f
        return _density_score(blob_n, scoring_terms, inn if inn_hit else None)

    if anchors:
        if not inn_hit and not any(a in blob_n for a in anchors):
            return 0.0
        return _density_score(blob_n, anchors, inn)

    return _density_score(blob_n, terms_f, inn)


class EmaJsonIndex:
    """Loads EMA JSON feeds into memory with optional disk cache."""

    def __init__(self) -> None:
        self._cache: Dict[str, Tuple[float, Any]] = {}
        self._lock = asyncio.Lock()
        self._base = settings.EMA_JSON_BASE_URL.rstrip("/")
        self._ttl = max(60, int(settings.EMA_JSON_CACHE_TTL_SECONDS))
        self._cache_dir = _default_cache_dir()

    def _cache_path(self, feed_key: str) -> Path:
        return self._cache_dir / FEED_FILES[feed_key]

    def _ensure_cache_dir(self) -> None:
        candidates = [self._cache_dir, _runtime_cache_dir()]
        seen: set[Path] = set()
        last_err: Optional[BaseException] = None

        for candidate in candidates:
            try:
                resolved = candidate.expanduser()
                if resolved in seen:
                    continue
                seen.add(resolved)
                resolved.mkdir(parents=True, exist_ok=True)
                probe = resolved / ".write_test"
                probe.write_text("", encoding="utf-8")
                probe.unlink(missing_ok=True)
                if resolved != self._cache_dir:
                    logger.warning(
                        "EMA JSON cache directory %s was not writable; using %s",
                        self._cache_dir,
                        resolved,
                    )
                    self._cache_dir = resolved
                return
            except Exception as e:
                last_err = e

        raise last_err if last_err else RuntimeError("No writable EMA JSON cache directory")

    async def _download(self, feed_key: str) -> Any:
        name = FEED_FILES[feed_key]
        url = f"{self._base}/{name}"
        self._ensure_cache_dir()
        dest = self._cache_path(feed_key)
        timeout = httpx.Timeout(120.0)
        headers = {
            "User-Agent": "Clinical-Knowledge-Agent/1.0 (EMA JSON cache; contact: local)",
            "Accept": "application/json,text/plain,*/*",
        }
        last_err: Optional[BaseException] = None
        async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
            for attempt in range(5):
                try:
                    r = await client.get(url)
                    if r.status_code in (429, 503):
                        wait_s = min(90.0, (2**attempt) + random.uniform(0.25, 1.5))
                        logger.warning(
                            "EMA JSON %s HTTP %s — backing off %.1fs (attempt %s/5)",
                            feed_key,
                            r.status_code,
                            wait_s,
                            attempt + 1,
                        )
                        await asyncio.sleep(wait_s)
                        continue
                    r.raise_for_status()
                    text = r.text
                    dest.write_text(text, encoding="utf-8")
                    return json.loads(text)
                except Exception as e:
                    last_err = e
                    wait_s = min(60.0, (2**attempt) + random.uniform(0.25, 1.0))
                    logger.warning("EMA JSON download attempt %s failed for %s: %s", attempt + 1, feed_key, e)
                    await asyncio.sleep(wait_s)
        raise last_err if last_err else RuntimeError(f"EMA JSON download failed for {feed_key}")

    async def _load_feed(self, feed_key: str) -> Any:
        async with self._lock:
            now = time.time()
            if feed_key in self._cache:
                loaded_at, data = self._cache[feed_key]
                if now - loaded_at < self._ttl:
                    return data
            dest = self._cache_path(feed_key)
            try:
                if dest.exists() and now - dest.stat().st_mtime < self._ttl:
                    data = json.loads(dest.read_text(encoding="utf-8"))
                    self._cache[feed_key] = (now, data)
                    return data
            except Exception as e:
                logger.warning("EMA JSON cache read failed %s: %s", dest, e)
            try:
                data = await self._download(feed_key)
                self._cache[feed_key] = (now, data)
                return data
            except Exception as e:
                logger.error("EMA JSON download failed %s: %s", feed_key, e)
                if dest.exists():
                    try:
                        stale = json.loads(dest.read_text(encoding="utf-8"))
                        logger.warning("EMA JSON using stale on-disk cache for %s after download failure", feed_key)
                        self._cache[feed_key] = (now, stale)
                        return stale
                    except Exception as e2:
                        logger.warning("EMA JSON stale cache read failed %s: %s", dest, e2)
                empty: Dict[str, Any] = {"meta": {}, "data": []}
                self._cache[feed_key] = (now, empty)
                return empty

    @staticmethod
    def _extract_rows(payload: Any) -> List[Dict[str, Any]]:
        if isinstance(payload, list):
            return [x for x in payload if isinstance(x, dict)]
        if isinstance(payload, dict):
            if "data" in payload and isinstance(payload["data"], list):
                return [x for x in payload["data"] if isinstance(x, dict)]
        return []

    async def search_medicines(
        self,
        terms: List[str],
        inn: Optional[str],
        max_results: int,
        company_terms: Optional[List[str]] = None,
    ) -> List[Tuple[Dict[str, Any], float, str]]:
        raw = await self._load_feed("medicines")
        rows = self._extract_rows(raw)
        out: List[Tuple[Dict[str, Any], float, str]] = []
        for row in rows:
            identity = _norm(
                " ".join(
                    str(row.get(k, ""))
                    for k in (
                        "name_of_medicine",
                        "international_non_proprietary_name_common_name",
                        "active_substance",
                        "marketing_authorisation_developer_applicant_holder",
                        "ema_product_number",
                    )
                )
            )
            blob = _norm(
                " ".join(
                    str(row.get(k, ""))
                    for k in (
                        "name_of_medicine",
                        "international_non_proprietary_name_common_name",
                        "active_substance",
                        "therapeutic_indication",
                        "therapeutic_area_mesh",
                        "marketing_authorisation_developer_applicant_holder",
                        "ema_product_number",
                        "atc_code_human",
                    )
                )
            )
            sc = _score_row(blob, terms, inn, identity_blob=identity)
            sc = _apply_company_terms_gate(sc, company_terms, identity, blob)
            if sc > 0:
                out.append((row, sc, "medicines_catalog"))
        out.sort(key=lambda x: -x[1])
        return out[:max_results]

    async def search_post_authorisation(
        self,
        terms: List[str],
        inn: Optional[str],
        max_results: int,
        company_terms: Optional[List[str]] = None,
    ) -> List[Tuple[Dict[str, Any], float, str]]:
        raw = await self._load_feed("post_authorisation")
        rows = self._extract_rows(raw)
        out: List[Tuple[Dict[str, Any], float, str]] = []
        for row in rows:
            identity = _norm(
                " ".join(
                    str(row.get(k, ""))
                    for k in (
                        "name_of_medicine",
                        "international_non_proprietary_name_common_name",
                        "active_substance",
                        "ema_product_number",
                        "marketing_authorisation_developer_applicant_holder",
                    )
                )
            )
            blob = _norm(
                " ".join(
                    str(row.get(k, ""))
                    for k in (
                        "name_of_medicine",
                        "international_non_proprietary_name_common_name",
                        "active_substance",
                        "post_authorisation_procedure_status",
                        "therapeutic_area_mesh",
                        "ema_product_number",
                        "marketing_authorisation_developer_applicant_holder",
                    )
                )
            )
            sc = _score_row(blob, terms, inn, identity_blob=identity)
            sc = _apply_company_terms_gate(sc, company_terms, identity, blob)
            if sc > 0:
                out.append((row, sc, "post_authorisation"))
        out.sort(key=lambda x: -x[1])
        return out[:max_results]

    async def search_epar_documents(
        self,
        terms: List[str],
        inn: Optional[str],
        max_results: int,
        company_terms: Optional[List[str]] = None,
    ) -> List[Tuple[Dict[str, Any], float, str]]:
        raw = await self._load_feed("epar_documents")
        rows = self._extract_rows(raw)
        out: List[Tuple[Dict[str, Any], float, str]] = []
        for row in rows:
            blob = _norm(
                " ".join(
                    str(row.get(k, ""))
                    for k in ("name", "type", "reference_number", "document_url")
                )
            )
            sc = _score_row(blob, terms, inn)
            sc = _apply_company_terms_gate(sc, company_terms, "", blob)
            if sc > 0:
                out.append((row, sc, "epar_documents"))
        out.sort(key=lambda x: -x[1])
        return out[:max_results]

    async def search_all_documents(
        self,
        terms: List[str],
        inn: Optional[str],
        max_results: int,
        company_terms: Optional[List[str]] = None,
    ) -> List[Tuple[Dict[str, Any], float, str]]:
        raw = await self._load_feed("all_documents")
        rows = self._extract_rows(raw)
        out: List[Tuple[Dict[str, Any], float, str]] = []
        for row in rows:
            blob = _norm(
                " ".join(
                    str(row.get(k, ""))
                    for k in ("name", "type", "reference_number", "document_url")
                )
            )
            sc = _score_row(blob, terms, inn)
            sc = _apply_company_terms_gate(sc, company_terms, "", blob)
            if sc > 0:
                out.append((row, sc, "all_documents"))
        out.sort(key=lambda x: -x[1])
        return out[:max_results]

    async def search_guidance(
        self,
        terms: List[str],
        inn: Optional[str],
        max_results: int,
        company_terms: Optional[List[str]] = None,
    ) -> List[Tuple[Dict[str, Any], float, str]]:
        raw = await self._load_feed("guidance")
        rows = self._extract_rows(raw)
        out: List[Tuple[Dict[str, Any], float, str]] = []
        for row in rows:
            blob = _norm(" ".join(str(row.get(k, "")) for k in ("title", "summary", "categories")))
            sc = _score_row(blob, terms, inn)
            sc = _apply_company_terms_gate(sc, company_terms, "", blob)
            if sc > 0:
                out.append((row, sc, "guidance_pages"))
        out.sort(key=lambda x: -x[1])
        return out[:max_results]

    async def search_orphan(
        self,
        terms: List[str],
        inn: Optional[str],
        max_results: int,
        company_terms: Optional[List[str]] = None,
    ) -> List[Tuple[Dict[str, Any], float, str]]:
        raw = await self._load_feed("orphan_designations")
        rows = self._extract_rows(raw)
        out: List[Tuple[Dict[str, Any], float, str]] = []
        for row in rows:
            blob = _norm(
                " ".join(str(row.get(k, "")) for k in row.keys() if isinstance(row.get(k), (str, int, float)))
            )
            sc = _score_row(blob, terms, inn)
            sc = _apply_company_terms_gate(sc, company_terms, "", blob)
            if sc > 0:
                out.append((row, sc, "orphan_designations"))
        out.sort(key=lambda x: -x[1])
        return out[:max_results]

    async def search_shortages(
        self,
        terms: List[str],
        inn: Optional[str],
        max_results: int,
        company_terms: Optional[List[str]] = None,
    ) -> List[Tuple[Dict[str, Any], float, str]]:
        raw = await self._load_feed("shortages")
        rows = self._extract_rows(raw)
        out: List[Tuple[Dict[str, Any], float, str]] = []
        for row in rows:
            blob = _norm(
                " ".join(str(row.get(k, "")) for k in row.keys() if isinstance(row.get(k), (str, int, float)))
            )
            sc = _score_row(blob, terms, inn)
            sc = _apply_company_terms_gate(sc, company_terms, "", blob)
            if sc > 0:
                out.append((row, sc, "shortages"))
        out.sort(key=lambda x: -x[1])
        return out[:max_results]

    async def search_referrals(
        self,
        terms: List[str],
        inn: Optional[str],
        max_results: int,
        company_terms: Optional[List[str]] = None,
    ) -> List[Tuple[Dict[str, Any], float, str]]:
        raw = await self._load_feed("referrals")
        rows = self._extract_rows(raw)
        out: List[Tuple[Dict[str, Any], float, str]] = []
        for row in rows:
            blob = _norm(
                " ".join(str(row.get(k, "")) for k in row.keys() if isinstance(row.get(k), (str, int, float)))
            )
            sc = _score_row(blob, terms, inn)
            sc = _apply_company_terms_gate(sc, company_terms, "", blob)
            if sc > 0:
                out.append((row, sc, "referrals"))
        out.sort(key=lambda x: -x[1])
        return out[:max_results]

    async def search_non_epar_documents(
        self,
        terms: List[str],
        inn: Optional[str],
        max_results: int,
        company_terms: Optional[List[str]] = None,
    ) -> List[Tuple[Dict[str, Any], float, str]]:
        raw = await self._load_feed("non_epar_documents")
        rows = self._extract_rows(raw)
        out: List[Tuple[Dict[str, Any], float, str]] = []
        for row in rows:
            blob = _norm(
                " ".join(str(row.get(k, "")) for k in ("name", "type", "reference_number", "document_url"))
            )
            sc = _score_row(blob, terms, inn)
            sc = _apply_company_terms_gate(sc, company_terms, "", blob)
            if sc > 0:
                out.append((row, sc, "non_epar_documents"))
        out.sort(key=lambda x: -x[1])
        return out[:max_results]

    async def search_dhpc(
        self,
        terms: List[str],
        inn: Optional[str],
        max_results: int,
        company_terms: Optional[List[str]] = None,
    ) -> List[Tuple[Dict[str, Any], float, str]]:
        raw = await self._load_feed("dhpc")
        rows = self._extract_rows(raw)
        out: List[Tuple[Dict[str, Any], float, str]] = []
        for row in rows:
            blob = _norm(
                " ".join(
                    str(row.get(k, ""))
                    for k in (
                        "name_of_medicine",
                        "active_substances",
                        "dhpc_type",
                        "referral_name",
                        "regulatory_outcome",
                        "therapeutic_area_mesh",
                        "procedure_number",
                    )
                )
            )
            identity = _norm(
                " ".join(
                    str(row.get(k, ""))
                    for k in (
                        "name_of_medicine",
                        "active_substances",
                        "referral_name",
                        "procedure_number",
                    )
                )
            )
            sc = _score_row(blob, terms, inn)
            sc = _apply_company_terms_gate(sc, company_terms, identity, blob)
            if sc > 0:
                out.append((row, sc, "dhpc"))
        out.sort(key=lambda x: -x[1])
        return out[:max_results]

    async def search_psusa(
        self,
        terms: List[str],
        inn: Optional[str],
        max_results: int,
        company_terms: Optional[List[str]] = None,
    ) -> List[Tuple[Dict[str, Any], float, str]]:
        raw = await self._load_feed("psusa")
        rows = self._extract_rows(raw)
        out: List[Tuple[Dict[str, Any], float, str]] = []
        for row in rows:
            blob = _norm(
                " ".join(
                    str(row.get(k, ""))
                    for k in (
                        "active_substance",
                        "active_substances_in_scope_of_procedure",
                        "related_medicines",
                        "procedure_number",
                        "regulatory_outcome",
                    )
                )
            )
            sc = _score_row(blob, terms, inn)
            sc = _apply_company_terms_gate(sc, company_terms, "", blob)
            if sc > 0:
                out.append((row, sc, "psusa"))
        out.sort(key=lambda x: -x[1])
        return out[:max_results]

    async def search_pip(
        self,
        terms: List[str],
        inn: Optional[str],
        max_results: int,
        company_terms: Optional[List[str]] = None,
    ) -> List[Tuple[Dict[str, Any], float, str]]:
        raw = await self._load_feed("pip")
        rows = self._extract_rows(raw)
        out: List[Tuple[Dict[str, Any], float, str]] = []
        for row in rows:
            blob = _norm(
                " ".join(
                    str(row.get(k, ""))
                    for k in (
                        "invented_name",
                        "active_substance",
                        "therapeutic_area",
                        "condition_indication",
                        "decision_type",
                        "pip_number",
                        "decision_number",
                    )
                )
            )
            sc = _score_row(blob, terms, inn)
            sc = _apply_company_terms_gate(sc, company_terms, "", blob)
            if sc > 0:
                out.append((row, sc, "pip"))
        out.sort(key=lambda x: -x[1])
        return out[:max_results]


ema_json_index = EmaJsonIndex()
