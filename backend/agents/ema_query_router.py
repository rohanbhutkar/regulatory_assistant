"""
LLM-assisted routing: extract search facets and intent for EMA / EU medicines queries.
"""
from __future__ import annotations

import json
import logging
import re
from typing import List

from agents.llm_agent import llm_agent
from config import settings
from models.schemas import EmaQueryFacets
from utils.cache import cache_manager

logger = logging.getLogger(__name__)

_ROUTER_SYSTEM = """You are a pharmaceutical regulatory search assistant. Extract structured facets from the user query for searching EMA public medicines data (EU / EMA).
Return ONLY valid JSON with keys: product_terms (array of strings, 1-4 short tokens: brand or product names), company_terms (array of strings, 0-4 lowercase fragments: marketing authorisation holder / applicant company if the user names a specific pharma company, e.g. ["boehringer","ingelheim"] or ["novartis"]; use [] if no company is specified or query is class-level only), inn (string or null), ema_product_number (string or null), pms_id (string or null), gtin (string or null), atc_code (string or null), intent (one of: product_profile, epar_documents, post_auth_variation, guidance, shortage, orphan, referral, dhpc, psusa, pip, non_epar_documents, general).
Intent rules:
- epar_documents: EPAR, assessment report, SmPC, refusal, withdrawal, European public assessment
- post_auth_variation: variation, type II, extension of indication, post-authorisation, label update
- guidance: guideline, scientific advice, ICH, procedural guidance
- shortage: shortage, supply disruption, availability
- orphan: orphan designation, rare disease designation
- referral: referral procedure, PRAC, safety review EU referral
- dhpc: DHPC, direct healthcare professional communication, dear doctor letter, HCP communication
- psusa: PSUSA, PSUR single assessment, periodic safety update
- pip: PIP, paediatric investigation plan, pediatric investigation plan
- non_epar_documents: non-EPAR EMA documents, consultations, committees (not EPAR-specific)
- product_profile: default for medicine/product questions
- general: else
"""


def _fallback_facets(query: str) -> EmaQueryFacets:
    q = query.lower()
    stop = {
        "what", "when", "where", "which", "about", "the", "a", "an", "for", "and", "or", "ema", "eu",
        "medicine", "medicines", "drug", "product", "tell", "me", "find", "search", "list", "show",
    }
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-%+]{1,}", query)
    terms: List[str] = []
    for w in words:
        wl = w.lower()
        if wl in stop or len(wl) < 3:
            continue
        terms.append(wl)
        if len(terms) >= 4:
            break
    if not terms:
        terms = ["medicine"]
    intent = "product_profile"
    if any(x in q for x in ("epar", "assessment report", " european public", "refusal", "withdrawn")):
        intent = "epar_documents"
    elif any(x in q for x in ("variation", "post-authorisation", "post authorization", "label update")):
        intent = "post_auth_variation"
    elif any(x in q for x in ("guideline", "guidance", "scientific advice", "ich")):
        intent = "guidance"
    elif "shortage" in q or "supply" in q:
        intent = "shortage"
    elif "orphan" in q:
        intent = "orphan"
    elif "referral" in q or "prac" in q:
        intent = "referral"
    elif "dhpc" in q or "healthcare professional communication" in q or "dear doctor" in q:
        intent = "dhpc"
    elif "psusa" in q or ("psur" in q and "single" in q) or "periodic safety update" in q:
        intent = "psusa"
    elif "pip" in q or "paediatric investigation" in q or "pediatric investigation" in q:
        intent = "pip"
    elif "non-epar" in q or "non epar" in q:
        intent = "non_epar_documents"
    company_terms: List[str] = []
    if "boehringer" in q and "ingelheim" in q:
        company_terms = ["boehringer", "ingelheim"]
    elif "boehringer" in q:
        company_terms = ["boehringer"]
    return EmaQueryFacets(product_terms=terms, company_terms=company_terms, intent=intent)


async def route_query(query: str) -> EmaQueryFacets:
    qn = (query or "").strip()
    cache_key = None
    if qn:
        cache_key = cache_manager._generate_key("ema_query_router", qn[:8000])
        cached = cache_manager.get(cache_key)
        if isinstance(cached, dict) and cached.get("intent"):
            try:
                return EmaQueryFacets(**cached)
            except Exception:
                pass

    try:
        raw = await llm_agent.generate_response(
            prompt=f"USER QUERY:\n{query}\n\nReturn JSON only, no markdown.",
            system_prompt=_ROUTER_SYSTEM,
        )
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        data = json.loads(text)
        terms = data.get("product_terms") or []
        if isinstance(terms, str):
            terms = [terms]
        terms = [str(t).strip().lower() for t in terms if str(t).strip()][:6]
        ct = data.get("company_terms") or []
        if isinstance(ct, str):
            ct = [ct]
        company_terms = [str(t).strip().lower() for t in ct if str(t).strip()][:6]
        facets = EmaQueryFacets(
            product_terms=terms,
            company_terms=company_terms,
            inn=data.get("inn"),
            ema_product_number=data.get("ema_product_number"),
            pms_id=data.get("pms_id"),
            gtin=data.get("gtin"),
            atc_code=data.get("atc_code"),
            intent=str(data.get("intent") or "general"),
        )
        if cache_key and int(settings.LLM_AUX_CACHE_TTL_SECONDS) > 0:
            cache_manager.set(
                cache_key,
                facets.model_dump(),
                ttl=int(settings.LLM_AUX_CACHE_TTL_SECONDS),
            )
        return facets
    except Exception as e:
        logger.warning("EMA query router LLM failed, using fallback: %s", e)
        return _fallback_facets(query)
