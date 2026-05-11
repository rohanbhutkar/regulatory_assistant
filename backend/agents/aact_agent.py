"""
AACT (Aggregate Analysis of ClinicalTrials.gov) — live PostgreSQL (ctgov schema).

Connects when AACT_DB_USERNAME and AACT_DB_PASSWORD are set in the environment.
"""
from __future__ import annotations

import asyncio
import os
import re
import ssl
from typing import Any, Dict, List, Optional, Sequence

from config import settings
from models.schemas import ClinicalTrialResult

try:
    import asyncpg
except ImportError:  # pragma: no cover
    asyncpg = None  # type: ignore


def _ilike_pattern(q: str) -> str:
    """Safe ILIKE pattern from free text (limit length; escape wildcards)."""
    s = re.sub(r"[%_\\]", " ", (q or "").strip())[:280]
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) < 2:
        return ""
    return f"%{s}%"


def _aact_ssl_context() -> ssl.SSLContext:
    """TLS verify for asyncpg — certifi bundle and optional AACT_DB_SSL_CAFILE."""
    cafile = getattr(settings, "AACT_DB_SSL_CAFILE", "") or ""
    if cafile and os.path.isfile(cafile):
        return ssl.create_default_context(cafile=cafile)
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:  # pragma: no cover
        return ssl.create_default_context()


def _row_to_dict(row: Any) -> Dict[str, Any]:
    d = dict(row)
    out: Dict[str, Any] = {}
    for k, v in d.items():
        if v is None:
            out[k] = None
        elif hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


class AACTAgent:
    """Query the public CTTI AACT PostgreSQL database (schema ctgov)."""

    @staticmethod
    def like_pattern(q: str) -> str:
        """Wildcard pattern for ILIKE ($1); empty string means too vague to search."""
        return _ilike_pattern(q)

    def __init__(self) -> None:
        self._pool: Optional[Any] = None
        self._pool_lock = asyncio.Lock()

    @property
    def enabled(self) -> bool:
        return bool(
            asyncpg
            and (settings.AACT_DB_USERNAME or "").strip()
            and (settings.AACT_DB_PASSWORD or "").strip()
        )

    async def _get_pool(self) -> Any:
        if not asyncpg:
            raise RuntimeError("asyncpg is not installed; pip install asyncpg")
        if not self.enabled:
            raise RuntimeError("AACT credentials missing (AACT_DB_USERNAME / AACT_DB_PASSWORD)")

        async with self._pool_lock:
            if self._pool is None:
                ssl_ctx: Optional[ssl.SSLContext] = None
                if settings.AACT_DB_SSL:
                    ssl_ctx = _aact_ssl_context()

                self._pool = await asyncpg.create_pool(
                    host=settings.AACT_DB_HOST,
                    port=settings.AACT_DB_PORT,
                    user=settings.AACT_DB_USERNAME.strip(),
                    password=settings.AACT_DB_PASSWORD,
                    database=settings.AACT_DB_NAME,
                    ssl=ssl_ctx,
                    min_size=1,
                    max_size=5,
                    command_timeout=120,
                )
                print(
                    f"✅ AACT pool ready → {settings.AACT_DB_HOST}:{settings.AACT_DB_PORT}/"
                    f"{settings.AACT_DB_NAME} as {settings.AACT_DB_USERNAME.strip()}"
                )
        return self._pool

    async def execute_custom_query(
        self,
        sql_query: str,
        params: Optional[Sequence[Any]] = None,
    ) -> Dict[str, Any]:
        """Run a parameterized SELECT; params use $1, $2, … (asyncpg)."""
        if not self.enabled:
            return {"success": False, "error": "AACT not configured", "results": []}
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(sql_query, *(params or ()))
            return {"success": True, "results": [_row_to_dict(r) for r in rows]}
        except Exception as e:
            err = str(e)
            print(f"❌ AACT execute_custom_query failed: {e}")
            hint: Optional[str] = None
            if "CERTIFICATE_VERIFY_FAILED" in err or "certificate has expired" in err.lower():
                hint = (
                    "TLS verification failed (often an expired certificate on the AACT host, "
                    "not your CTTI password). Renewal is on the operator side; "
                    "see https://aact.ctti-clinicaltrials.org/ or CTTI support."
                )
                print(f"ℹ️ AACT: {hint}")
            return {"success": False, "error": err, "results": [], **({"hint": hint} if hint else {})}

    async def search_studies(
        self,
        query: str,
        max_results: int = 50,
        node_description: str = "",
        node_parameters: Optional[dict] = None,
    ) -> List[ClinicalTrialResult]:
        """Full-text-style search across titles, sponsor, summary, conditions, interventions."""
        if not self.enabled:
            print("⚠️ AACTAgent: credentials not set; returning no rows.")
            return []

        max_results = max(1, min(int(max_results or 50), 100))
        pattern = _ilike_pattern(query)
        if not pattern:
            return []

        sql = """
SELECT
  s.nct_id,
  s.brief_title,
  s.official_title,
  s.overall_status,
  s.phase,
  s.enrollment,
  s.start_date,
  COALESCE(s.completion_date, s.primary_completion_date) AS completion_date,
  s.lead_sponsor_name,
  bs.description AS brief_summary,
  cond.names AS condition,
  intr.names AS intervention_name,
  fac.city AS location_city,
  fac.state AS location_state,
  fac.country AS location_country
FROM ctgov.studies s
LEFT JOIN ctgov.brief_summaries bs ON bs.nct_id = s.nct_id
LEFT JOIN LATERAL (
  SELECT string_agg(DISTINCT c.name, ', ' ORDER BY c.name) AS names
  FROM ctgov.conditions c WHERE c.nct_id = s.nct_id
) cond ON TRUE
LEFT JOIN LATERAL (
  SELECT string_agg(DISTINCT i.name, ', ' ORDER BY i.name) AS names
  FROM ctgov.interventions i WHERE i.nct_id = s.nct_id
) intr ON TRUE
LEFT JOIN LATERAL (
  SELECT f.city, f.state, f.country
  FROM ctgov.facilities f
  WHERE f.nct_id = s.nct_id
  ORDER BY f.id NULLS LAST
  LIMIT 1
) fac ON TRUE
WHERE
  s.brief_title ILIKE $1
  OR s.official_title ILIKE $1
  OR s.lead_sponsor_name ILIKE $1
  OR bs.description ILIKE $1
  OR EXISTS (
    SELECT 1 FROM ctgov.conditions c
    WHERE c.nct_id = s.nct_id AND c.name ILIKE $1
  )
  OR EXISTS (
    SELECT 1 FROM ctgov.interventions i
    WHERE i.nct_id = s.nct_id AND i.name ILIKE $1
  )
ORDER BY s.start_date DESC NULLS LAST
LIMIT $2;
"""
        res = await self.execute_custom_query(sql, [pattern, max_results])
        if not res.get("success"):
            return []
        return self._rows_to_trials(res["results"], default_relevance=0.75)

    def _rows_to_trials(
        self,
        rows: List[Dict[str, Any]],
        default_relevance: float = 0.8,
    ) -> List[ClinicalTrialResult]:
        trials: List[ClinicalTrialResult] = []
        for row in rows:
            try:
                loc_parts = [
                    x
                    for x in (
                        row.get("location_city"),
                        row.get("location_state"),
                        row.get("location_country"),
                    )
                    if x
                ]
                location = ", ".join(str(x) for x in loc_parts) if loc_parts else ""

                enr = row.get("enrollment")
                if enr is not None:
                    try:
                        enr = int(enr)
                    except (TypeError, ValueError):
                        enr = None

                trials.append(
                    ClinicalTrialResult(
                        nct_id=str(row.get("nct_id") or ""),
                        title=str(row.get("brief_title") or row.get("official_title") or ""),
                        condition=row.get("condition") or None,
                        intervention=row.get("intervention_name") or None,
                        sponsor=row.get("lead_sponsor_name") or None,
                        status=row.get("overall_status") or None,
                        phase=str(row.get("phase") or "") if row.get("phase") is not None else None,
                        enrollment=enr,
                        start_date=str(row["start_date"]) if row.get("start_date") else None,
                        completion_date=str(row["completion_date"])
                        if row.get("completion_date")
                        else None,
                        description=row.get("brief_summary") or None,
                        location=location or None,
                        relevance_score=default_relevance,
                    )
                )
            except Exception as e:
                print(f"⚠️ AACT row → ClinicalTrialResult failed: {e}")
                continue
        print(f"📊 AACT returned {len(trials)} trial(s)")
        return trials

    async def get_study_details(self, nct_id: str) -> Optional[ClinicalTrialResult]:
        if not self.enabled:
            return None
        nct = (nct_id or "").strip().upper()
        if not re.match(r"^NCT\d{8}$", nct):
            return None

        sql = """
SELECT
  s.nct_id,
  s.brief_title,
  s.official_title,
  s.overall_status,
  s.phase,
  s.enrollment,
  s.start_date,
  COALESCE(s.completion_date, s.primary_completion_date) AS completion_date,
  s.lead_sponsor_name,
  bs.description AS brief_summary,
  cond.names AS condition,
  intr.names AS intervention_name,
  fac.city AS location_city,
  fac.state AS location_state,
  fac.country AS location_country
FROM ctgov.studies s
LEFT JOIN ctgov.brief_summaries bs ON bs.nct_id = s.nct_id
LEFT JOIN LATERAL (
  SELECT string_agg(DISTINCT c.name, ', ' ORDER BY c.name) AS names
  FROM ctgov.conditions c WHERE c.nct_id = s.nct_id
) cond ON TRUE
LEFT JOIN LATERAL (
  SELECT string_agg(DISTINCT i.name, ', ' ORDER BY i.name) AS names
  FROM ctgov.interventions i WHERE i.nct_id = s.nct_id
) intr ON TRUE
LEFT JOIN LATERAL (
  SELECT f.city, f.state, f.country
  FROM ctgov.facilities f
  WHERE f.nct_id = s.nct_id
  ORDER BY f.id NULLS LAST
  LIMIT 1
) fac ON TRUE
WHERE s.nct_id = $1
LIMIT 1;
"""
        res = await self.execute_custom_query(sql, [nct])
        if not res.get("success") or not res["results"]:
            return None
        trials = self._rows_to_trials(res["results"], default_relevance=1.0)
        return trials[0] if trials else None

    async def get_study_statistics(self) -> Dict[str, Any]:
        if not self.enabled:
            return {"error": "AACT not configured"}
        res = await self.execute_custom_query(
            "SELECT COUNT(*)::bigint AS total FROM ctgov.studies;"
        )
        if not res.get("success") or not res["results"]:
            return {"error": res.get("error", "query failed")}
        total = res["results"][0].get("total")
        return {"source": "aact", "total_studies": int(total) if total is not None else 0}

    async def search_recent_updated(self, days: int, max_results: int) -> List[ClinicalTrialResult]:
        """Studies whose last_update_posted_date is within the last `days` days."""
        if not self.enabled:
            return []
        max_results = max(1, min(int(max_results or 50), 100))
        days = max(1, min(int(days or 30), 365))
        sql = """
SELECT
  s.nct_id,
  s.brief_title,
  s.official_title,
  s.overall_status,
  s.phase,
  s.enrollment,
  s.start_date,
  COALESCE(s.completion_date, s.primary_completion_date) AS completion_date,
  s.lead_sponsor_name,
  bs.description AS brief_summary,
  cond.names AS condition,
  intr.names AS intervention_name,
  fac.city AS location_city,
  fac.state AS location_state,
  fac.country AS location_country
FROM ctgov.studies s
LEFT JOIN ctgov.brief_summaries bs ON bs.nct_id = s.nct_id
LEFT JOIN LATERAL (
  SELECT string_agg(DISTINCT c.name, ', ' ORDER BY c.name) AS names
  FROM ctgov.conditions c WHERE c.nct_id = s.nct_id
) cond ON TRUE
LEFT JOIN LATERAL (
  SELECT string_agg(DISTINCT i.name, ', ' ORDER BY i.name) AS names
  FROM ctgov.interventions i WHERE i.nct_id = s.nct_id
) intr ON TRUE
LEFT JOIN LATERAL (
  SELECT f.city, f.state, f.country
  FROM ctgov.facilities f
  WHERE f.nct_id = s.nct_id
  ORDER BY f.id NULLS LAST
  LIMIT 1
) fac ON TRUE
WHERE s.last_update_posted_date >= (CURRENT_TIMESTAMP - ($1::int * INTERVAL '1 day'))
ORDER BY s.last_update_posted_date DESC NULLS LAST
LIMIT $2;
"""
        res = await self.execute_custom_query(sql, [days, max_results])
        if not res.get("success"):
            return []
        return self._rows_to_trials(res["results"], default_relevance=0.7)


aact_agent = AACTAgent()
