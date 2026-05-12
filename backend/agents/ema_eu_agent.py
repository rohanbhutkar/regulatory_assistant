"""
Unified EMA / EU medicines search: EMA bulk JSON + optional ePI FHIR + optional PMS read.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from agents.ema_epi_client import (
    bundle_ids_from_list_resource,
    ema_epi_client,
    extract_bundle_excerpt,
)
from agents.ema_json_index import augment_terms_from_query, ema_json_index
from agents.ema_pms_client import ema_pms_client
from agents.ema_query_router import route_query
from config import settings
from models.schemas import EmaSearchResult
from utils.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)

LIMIT_NOTE = (
    "ePI pilot covers a subset of EU medicines; full catalogue uses EMA JSON feeds. "
    "National packs may differ from centrally authorised data."
)


def _excerpt_from_medicine_row(row: Dict[str, Any]) -> str:
    parts = [
        str(row.get("name_of_medicine") or "").strip(),
        f"INN: {row.get('international_non_proprietary_name_common_name') or row.get('active_substance') or ''}",
        f"Status: {row.get('medicine_status') or ''}",
        (str(row.get("therapeutic_indication") or ""))[:500],
    ]
    return " | ".join(p for p in parts if p and p != "INN: " and p != "Status: ")


def _excerpt_epar_row(row: Dict[str, Any]) -> str:
    return f"{row.get('type') or 'Document'}: {row.get('name') or ''}"[:600]


def _excerpt_guidance_row(row: Dict[str, Any]) -> str:
    s = str(row.get("summary") or "")[:500]
    return f"{row.get('title') or ''}: {s}"


def _dedupe_key(r: EmaSearchResult) -> Tuple[str, str]:
    num = r.ema_product_number or ""
    sid = str(
        r.metadata.get("id")
        or r.metadata.get("document_id")
        or r.metadata.get("bundle_id")
        or ""
    )
    return (r.sub_source, num or sid or r.title[:120])


async def search_ema_eu(query: str, max_results: int = 25) -> List[EmaSearchResult]:
    await rate_limiter.acquire("ema_eu")
    facets = await route_query(query)
    company_terms = [
        c.strip().lower() for c in (facets.company_terms or []) if len(c.strip()) >= 2
    ][:8]
    if not company_terms:
        ql = (query or "").lower()
        if "boehringer" in ql and "ingelheim" in ql:
            company_terms = ["boehringer", "ingelheim"]
        elif "boehringer" in ql:
            company_terms = ["boehringer"]

    terms = list(facets.product_terms) or [query.lower()[:80]]
    terms = augment_terms_from_query(query, terms)
    for c in reversed(company_terms):
        if c not in terms:
            terms.insert(0, c)
    if facets.atc_code and str(facets.atc_code).strip():
        terms = [str(facets.atc_code).strip().lower()] + terms
    inn = (facets.inn or "").strip().lower() or None
    intent = facets.intent or "general"

    tasks: List[Any] = []

    async def run_medicines() -> List[Tuple[Dict[str, Any], float, str]]:
        if facets.ema_product_number:
            by_num = await ema_json_index.search_medicines(
                [str(facets.ema_product_number)], inn, max_results, company_terms
            )
            if by_num:
                return by_num
        return await ema_json_index.search_medicines(
            terms, inn, max_results, company_terms
        )

    if intent == "epar_documents":
        tasks = [
            run_medicines(),
            ema_json_index.search_epar_documents(terms, inn, max_results, company_terms),
        ]
    elif intent == "post_auth_variation":
        tasks = [
            run_medicines(),
            ema_json_index.search_post_authorisation(
                terms, inn, max_results, company_terms
            ),
        ]
    elif intent == "guidance":
        tasks = [
            ema_json_index.search_guidance(terms, inn, max_results, company_terms)
        ]
    elif intent == "shortage":
        tasks = [
            run_medicines(),
            ema_json_index.search_shortages(terms, inn, max_results, company_terms),
        ]
    elif intent == "orphan":
        tasks = [
            run_medicines(),
            ema_json_index.search_orphan(terms, inn, max_results, company_terms),
        ]
    elif intent == "referral":
        tasks = [
            run_medicines(),
            ema_json_index.search_referrals(terms, inn, max_results, company_terms),
        ]
    elif intent == "dhpc":
        tasks = [
            run_medicines(),
            ema_json_index.search_dhpc(terms, inn, max_results, company_terms),
        ]
    elif intent == "psusa":
        tasks = [
            run_medicines(),
            ema_json_index.search_psusa(terms, inn, max_results, company_terms),
        ]
    elif intent == "pip":
        tasks = [
            run_medicines(),
            ema_json_index.search_pip(terms, inn, max_results, company_terms),
        ]
    elif intent == "non_epar_documents":
        tasks = [
            run_medicines(),
            ema_json_index.search_non_epar_documents(
                terms, inn, max_results, company_terms
            ),
        ]
    else:
        cap = max(1, min(max_results, 12))
        tasks = [
            run_medicines(),
            ema_json_index.search_epar_documents(
                terms, inn, min(10, cap), company_terms
            ),
            ema_json_index.search_post_authorisation(
                terms, inn, min(10, cap), company_terms
            ),
            ema_json_index.search_guidance(terms, inn, min(8, cap), company_terms),
            ema_json_index.search_non_epar_documents(
                terms, inn, min(6, cap), company_terms
            ),
            ema_json_index.search_dhpc(terms, inn, min(5, cap), company_terms),
            ema_json_index.search_psusa(terms, inn, min(5, cap), company_terms),
            ema_json_index.search_pip(terms, inn, min(5, cap), company_terms),
        ]

    gathered = await asyncio.gather(*tasks, return_exceptions=True)
    merged: List[EmaSearchResult] = []
    _n_tasks = len(gathered)
    _n_exc = sum(1 for b in gathered if isinstance(b, Exception))
    if _n_exc:
        logger.warning(
            "EMA EU: %s/%s parallel index tasks raised exceptions (terms=%r intent=%s)",
            _n_exc,
            _n_tasks,
            terms[:5],
            intent,
        )

    def append_rows(block: Any) -> None:
        if not isinstance(block, list):
            return
        for item in block:
            if not isinstance(item, tuple) or len(item) < 3:
                continue
            row, score, sub = item[0], item[1], item[2]
            if sub == "medicines_catalog":
                mu = str(row.get("medicine_url") or "").strip()
                merged.append(
                    EmaSearchResult(
                        title=str(row.get("name_of_medicine") or "Medicine"),
                        sub_source=sub,
                        excerpt=_excerpt_from_medicine_row(row),
                        relevance_score=float(score),
                        ema_product_number=str(row.get("ema_product_number") or "") or None,
                        source_urls=[mu] if mu else [],
                        limitations=LIMIT_NOTE,
                        metadata={
                            "medicine_status": row.get("medicine_status"),
                            "opinion_status": row.get("opinion_status"),
                            "atc_code_human": row.get("atc_code_human"),
                            "orphan_medicine": row.get("orphan_medicine"),
                            "prime_priority_medicine": row.get("prime_priority_medicine"),
                            "biosimilar": row.get("biosimilar"),
                            "generic": row.get("generic"),
                            "advanced_therapy": row.get("advanced_therapy"),
                            "conditional_approval": row.get("conditional_approval"),
                            "exceptional_circumstances": row.get("exceptional_circumstances"),
                            "accelerated_assessment": row.get("accelerated_assessment"),
                            "additional_monitoring": row.get("additional_monitoring"),
                            "patient_safety": row.get("patient_safety"),
                            "marketing_authorisation_date": row.get("marketing_authorisation_date"),
                            "european_commission_decision_date": row.get("european_commission_decision_date"),
                            "revision_number": row.get("revision_number"),
                        },
                    )
                )
            elif sub in ("epar_documents", "all_documents", "non_epar_documents"):
                url = str(row.get("document_url") or "").strip()
                merged.append(
                    EmaSearchResult(
                        title=str(row.get("name") or "Document"),
                        sub_source=sub,
                        excerpt=_excerpt_epar_row(row),
                        relevance_score=float(score),
                        source_urls=[url] if url else [],
                        limitations=LIMIT_NOTE,
                        metadata={"reference_number": row.get("reference_number"), "type": row.get("type")},
                    )
                )
            elif sub == "guidance_pages":
                url = str(row.get("general_url") or "").strip()
                merged.append(
                    EmaSearchResult(
                        title=str(row.get("title") or "Guidance"),
                        sub_source=sub,
                        excerpt=_excerpt_guidance_row(row),
                        relevance_score=float(score),
                        source_urls=[url] if url else [],
                        limitations=LIMIT_NOTE,
                        metadata={"categories": row.get("categories")},
                    )
                )
            elif sub == "post_authorisation":
                merged.append(
                    EmaSearchResult(
                        title=str(row.get("name_of_medicine") or "Post-authorisation"),
                        sub_source=sub,
                        excerpt=_excerpt_from_medicine_row(row)
                        + f" | Procedure: {row.get('post_authorisation_procedure_status')}",
                        relevance_score=float(score),
                        ema_product_number=str(row.get("ema_product_number") or "") or None,
                        source_urls=[],
                        limitations=LIMIT_NOTE,
                        metadata={k: row.get(k) for k in list(row.keys())[:30]},
                    )
                )
            elif sub == "dhpc":
                url = str(row.get("dhpc_url") or "").strip()
                title = f"{row.get('name_of_medicine') or 'DHPC'} — {row.get('dhpc_type') or ''}"
                merged.append(
                    EmaSearchResult(
                        title=str(title.strip(" —") or "DHPC"),
                        sub_source=sub,
                        excerpt=(
                            f"{row.get('regulatory_outcome') or ''} | {row.get('referral_name') or ''} | "
                            f"{row.get('active_substances') or ''}"
                        )[:700],
                        relevance_score=float(score),
                        source_urls=[url] if url else [],
                        limitations=LIMIT_NOTE,
                        metadata={
                            "procedure_number": row.get("procedure_number"),
                            "dissemination_date": row.get("dissemination_date"),
                            "dhpc_type": row.get("dhpc_type"),
                        },
                    )
                )
            elif sub == "psusa":
                url = str(row.get("psusa_url") or "").strip()
                merged.append(
                    EmaSearchResult(
                        title=str(row.get("active_substance") or row.get("related_medicines") or "PSUSA"),
                        sub_source=sub,
                        excerpt=(
                            f"Procedure {row.get('procedure_number') or ''} | Outcome: {row.get('regulatory_outcome') or ''} | "
                            f"{row.get('active_substances_in_scope_of_procedure') or ''}"
                        )[:700],
                        relevance_score=float(score),
                        source_urls=[url] if url else [],
                        limitations=LIMIT_NOTE,
                        metadata={
                            "procedure_number": row.get("procedure_number"),
                            "regulatory_outcome": row.get("regulatory_outcome"),
                        },
                    )
                )
            elif sub == "pip":
                url = str(row.get("pip_url") or "").strip()
                merged.append(
                    EmaSearchResult(
                        title=str(row.get("invented_name") or row.get("active_substance") or "PIP"),
                        sub_source=sub,
                        excerpt=(
                            f"{row.get('condition_indication') or ''} | {row.get('decision_type') or ''} | "
                            f"PIP {row.get('pip_number') or ''}"
                        )[:700],
                        relevance_score=float(score),
                        source_urls=[url] if url else [],
                        limitations=LIMIT_NOTE,
                        metadata={
                            "pip_number": row.get("pip_number"),
                            "decision_date": row.get("decision_date"),
                            "decision_type": row.get("decision_type"),
                        },
                    )
                )
            elif sub in ("orphan_designations", "shortages", "referrals"):
                blob = " ".join(str(row.get(k, "")) for k in list(row.keys())[:14])
                merged.append(
                    EmaSearchResult(
                        title=str(row.get("name_of_medicine") or row.get("name") or row.get("title") or sub),
                        sub_source=sub,
                        excerpt=blob[:700],
                        relevance_score=float(score),
                        source_urls=[],
                        limitations=LIMIT_NOTE,
                        metadata={k: row.get(k) for k in list(row.keys())[:20]},
                    )
                )

    for block in gathered:
        if isinstance(block, Exception):
            logger.warning("EMA JSON task failed: %s", block)
            continue
        append_rows(block)

    if not merged and (query or "").strip():
        # search_medicines scores each term as a substring in the row blob — a single long
        # "fused" string almost never matches; use distinct query words instead.
        seen_w: Set[str] = set()
        fuse_terms: List[str] = []
        for w in query.replace(",", " ").split():
            wl = w.strip().lower()
            if len(wl) > 2 and wl not in seen_w:
                seen_w.add(wl)
                fuse_terms.append(wl)
        fuse_terms = fuse_terms[:16]
        routed_set = {t.strip().lower() for t in terms if len(t.strip()) > 2}
        # Retry when we have extra words beyond what the router passed, or any words if router was empty.
        extra_words = [t for t in fuse_terms if t not in routed_set]
        if fuse_terms and (extra_words or not routed_set):
            try:
                fb = await ema_json_index.search_medicines(
                    fuse_terms,
                    None,
                    max(5, min(max_results, 18)),
                    company_terms,
                )
                before = len(merged)
                append_rows(fb)
                logger.info(
                    "EMA EU: fallback medicines search added %s row(s) (terms=%r)",
                    len(merged) - before,
                    fuse_terms[:8],
                )
            except Exception as ex:
                logger.warning("EMA EU: fallback medicines search failed: %s", ex)

        if not merged and intent == "pip" and fuse_terms:
            # PIP intent often reflects procedural / legal questions (Reg 1901/2006, PDCO, waivers).
            # The PIP JSON feed is product-level decisions; add guidance + non-EPAR when still empty.
            try:
                cap = max(6, min(max_results, 18))
                fb_g, fb_n = await asyncio.gather(
                    ema_json_index.search_guidance(fuse_terms, None, cap, company_terms),
                    ema_json_index.search_non_epar_documents(
                        fuse_terms, None, min(cap, 14), company_terms
                    ),
                )
                before = len(merged)
                append_rows(fb_g)
                append_rows(fb_n)
                logger.info(
                    "EMA EU: pip intent fallback added %s row(s) from guidance/non-EPAR (terms=%r)",
                    len(merged) - before,
                    fuse_terms[:8],
                )
            except Exception as ex:
                logger.warning("EMA EU: pip fallback guidance/non-epar failed: %s", ex)
    if not merged:
        logger.warning(
            "EMA EU: empty merged result (query=%r terms=%r intent=%s exceptions=%s/%s)",
            (query or "")[:200],
            terms[:6],
            intent,
            _n_exc,
            _n_tasks,
        )

    # ePI FHIR (pilot) — List → BundleById when paths resolve on gateway
    if settings.EMA_EPI_ENABLED:
        title_q = " ".join(terms[:3]) if terms else query[:100]
        try:
            epi_resources = await ema_epi_client.search_by_title(title_q)
            cap_chars = settings.EMA_EPI_MAX_BUNDLE_CHARS
            bundles_fetched = 0
            max_bundle_hits = 3
            for res in epi_resources[:3]:
                if not isinstance(res, dict):
                    continue
                rtype = res.get("resourceType")
                if rtype == "List":
                    b_ids = bundle_ids_from_list_resource(res)
                    if not b_ids and res.get("id"):
                        lst = await ema_epi_client.fetch_list_by_id(str(res["id"]))
                        if isinstance(lst, dict) and lst.get("resourceType") == "List":
                            b_ids = bundle_ids_from_list_resource(lst)
                    for bid in b_ids:
                        if bundles_fetched >= max_bundle_hits:
                            break
                        b = await ema_epi_client.fetch_bundle_by_id(bid)
                        bundles_fetched += 1
                        ex = extract_bundle_excerpt(b, cap_chars)[:2500] if b else ""
                        merged.append(
                            EmaSearchResult(
                                title=f"ePI Bundle {bid[:48]}",
                                sub_source="epi_fhir",
                                excerpt=ex or "(empty bundle text)",
                                relevance_score=1.05,
                                source_urls=[],
                                limitations="EMA ePI pilot subset. If no hits, set EMA_EPI_BASE_URL/paths from developer portal Try it.",
                                metadata={"resource_type": "Bundle", "bundle_id": bid},
                            )
                        )
                else:
                    ex = extract_bundle_excerpt(res, min(4000, cap_chars))[:2000]
                    merged.append(
                        EmaSearchResult(
                            title=f"ePI {rtype or 'resource'} ({title_q[:60]})",
                            sub_source="epi_fhir",
                            excerpt=ex or "(no narrative text in resource)",
                            relevance_score=0.95,
                            source_urls=[],
                            limitations="EMA ePI pilot; paths auto-probed from EMA_EPI_*_PATH_CANDIDATES.",
                            metadata={"resource_type": rtype},
                        )
                    )
        except Exception as e:
            logger.info("EMA ePI search skipped or failed: %s", e)

        if facets.pms_id or facets.gtin:
            try:
                bundles = await ema_epi_client.search_by_bundle_params(
                    pms_id=facets.pms_id,
                    gtin=facets.gtin,
                    language="en",
                )
                for b in bundles[:3]:
                    ex = extract_bundle_excerpt(b, settings.EMA_EPI_MAX_BUNDLE_CHARS)[:2500]
                    merged.append(
                        EmaSearchResult(
                            title="ePI bundle (PMS/GTIN query)",
                            sub_source="epi_fhir",
                            excerpt=ex,
                            relevance_score=1.1,
                            source_urls=[],
                            limitations=LIMIT_NOTE,
                            metadata={},
                        )
                    )
            except Exception as e:
                logger.debug("ePI bundle params: %s", e)

    # Optional PMS authenticated read
    if settings.EMA_PMS_READ_ENABLED and facets.pms_id:
        pms_bundle = await ema_pms_client.read_medicinal_product_everything(facets.pms_id)
        if pms_bundle:
            ex = extract_bundle_excerpt(pms_bundle, settings.EMA_EPI_MAX_BUNDLE_CHARS)[:4000]
            merged.append(
                EmaSearchResult(
                    title=f"PMS MedicinalProductDefinition ($everything) {facets.pms_id}",
                    sub_source="pms_fhir_read",
                    excerpt=ex,
                    relevance_score=1.5,
                    source_urls=[],
                    limitations="Authenticated PMS FHIR read; structured regulatory data.",
                    metadata={"pms_id": facets.pms_id},
                )
            )

    # Dedupe + sort
    seen: Set[Tuple[str, str]] = set()
    out: List[EmaSearchResult] = []
    merged.sort(key=lambda x: -x.relevance_score)
    for r in merged:
        k = _dedupe_key(r)
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
        if len(out) >= max_results:
            break
    return out


class EmaEuAgent:
    async def search(self, query: str, max_results: int = 25) -> List[EmaSearchResult]:
        return await search_ema_eu(query, max_results=max_results)


ema_eu_agent = EmaEuAgent()
