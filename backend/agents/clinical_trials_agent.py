"""
ClinicalTrials.gov API Agent with AACT Database Integration
"""
import asyncio
import re
import time
import requests
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from config import settings, CLINICAL_TRIALS_ENDPOINTS
from utils.logger import log_api_call, log_error
from utils.cache import cache_manager
from utils.rate_limiter import rate_limiter
from models.schemas import ClinicalTrialResult
from agents.aact_agent import aact_agent
from datetime import datetime, timedelta

# ClinicalTrials.gov v2 rejects long natural-language `query.term` (400). Use sponsors / keywords instead.
# v2 ANDs each space-separated token; ~11+ distinct terms returns "Too complicated query" (HTTP 400).
_CTGOV_QUERY_TERM_MAX_TOKENS = 8
_CTGOV_STOPWORDS = frozenset(
    {
        "what",
        "types",
        "type",
        "which",
        "where",
        "when",
        "why",
        "how",
        "who",
        "whom",
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "to",
        "of",
        "in",
        "on",
        "at",
        "for",
        "with",
        "from",
        "by",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "would",
        "could",
        "should",
        "may",
        "might",
        "will",
        "can",
        "this",
        "that",
        "these",
        "those",
        "their",
        "them",
        "they",
        "we",
        "you",
        "it",
        "its",
        "look",
        "looked",
        "looking",
        "show",
        "give",
        "get",
        "find",
        "search",
        "tell",
        "right",
        "now",
        "just",
        "like",
        "such",
        "any",
        "some",
        "all",
        "each",
        "both",
        "other",
        "into",
        "about",
        "over",
        "up",
        "out",
        "etc",
        "ask",
        "asking",
        "interested",
        "interest",
        "there",
        "here",
    }
)

_CT_NCT_ID = re.compile(r"^NCT\d{8}$", re.I)
# e.g. "would boehringer ingelheim be asking" → boehringer ingelheim
_CT_SPONS_AFTER_WOULD = re.compile(
    r"\bwould\s+([a-z][a-z0-9'-]*(?:\s+[a-z][a-z0-9'-]*){0,4})\s+be\b",
    re.I,
)
_CT_TITLE_SPONS = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b")
_CT_SPONS_BAD_FIRST = frozenset(
    {
        "Regulatory",
        "Clinical",
        "Current",
        "What",
        "Which",
        "Phase",
        "United",
        "European",
        "Primary",
        "Secondary",
        "Study",
        "Trial",
        "Patient",
        "Medical",
        "Health",
        "Drug",
        "Safety",
        "Efficacy",
        "Types",
        "Other",
        "Additional",
        "New",
        "Recent",
    }
)

_CT_STUDY_FIELDS = (
    "NCTId,BriefTitle,Condition,InterventionName,LeadSponsorName,OverallStatus,"
    "Phase,EnrollmentCount,StartDate,CompletionDate,BriefSummary,LocationCountry"
)

_DEFAULT_CT_USER_AGENT = (
    "RegulatoryAssistant/1.0 (+https://clinicaltrials.gov/data-api/about-api; research)"
)


class ClinicalTrialsAgent:
    def __init__(self):
        self.base_url = settings.CLINICAL_TRIALS_API_BASE
        # requests (urllib3) TLS is accepted by clinicaltrials.gov; httpx often gets HTML 403 from the CDN.
        self.request_timeout_sec = 15.0
        self.use_aact = aact_agent.enabled

    @staticmethod
    def _normalize_search_text(q: str) -> str:
        if not q or not isinstance(q, str):
            return ""
        q = q.replace("\r\n", "\n").strip()
        q = re.sub(r"\s+", " ", q)
        return q.strip()

    @staticmethod
    def _cap_ctgov_query_term(term: str) -> str:
        """Limit ANDed tokens — v2 errors with 'Too complicated query' when there are too many."""
        if not term or not isinstance(term, str):
            return ""
        seen: set[str] = set()
        out: List[str] = []
        for tok in term.split():
            t = tok.strip()
            if len(t) < 2:
                continue
            key = t.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(t)
            if len(out) >= _CTGOV_QUERY_TERM_MAX_TOKENS:
                break
        return " ".join(out)

    @staticmethod
    def _keyword_query_term(normalized: str) -> str:
        q = normalized.lower()
        q = re.sub(r"[\?\!\.]+$", "", q)
        words = re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)?", q)
        seen: set[str] = set()
        out: List[str] = []
        for w in words:
            if w in _CTGOV_STOPWORDS or len(w) < 3:
                continue
            if w in seen:
                continue
            seen.add(w)
            out.append(w)
            if len(out) >= _CTGOV_QUERY_TERM_MAX_TOKENS:
                break
        return " ".join(out)

    @staticmethod
    def _try_would_be_sponsor(normalized: str) -> Optional[str]:
        m = _CT_SPONS_AFTER_WOULD.search(normalized)
        if not m:
            return None
        s = " ".join(m.group(1).split())
        if len(s) < 5 or len(s) > 120:
            return None
        return s

    @staticmethod
    def _try_title_case_sponsor(raw: str) -> Optional[str]:
        best: Optional[str] = None
        for m in _CT_TITLE_SPONS.finditer(raw):
            chunk = m.group(1).strip()
            parts = chunk.split()
            if not parts:
                continue
            if parts[0] in _CT_SPONS_BAD_FIRST:
                continue
            if len(chunk) < 8 or len(chunk) > 120:
                continue
            if best is None or len(chunk) > len(best):
                best = chunk
        return best

    def _studies_list_params(self, query: str, max_results: int) -> Dict[str, Any]:
        base: Dict[str, Any] = {
            "pageSize": min(max_results, 100),
            "fields": _CT_STUDY_FIELDS,
            "format": "json",
        }
        raw = query if isinstance(query, str) else ""
        normalized = self._normalize_search_text(raw)
        if not normalized:
            return {**base, "query.term": "clinical trial"}

        tid = normalized.strip()
        if _CT_NCT_ID.match(tid):
            return {**base, "query.id": tid.upper()}

        sponsor = self._try_would_be_sponsor(normalized) or self._try_title_case_sponsor(raw)
        if sponsor:
            return {**base, "query.spons": sponsor}

        term = self._keyword_query_term(normalized)
        if not term:
            term = " ".join(normalized[:400].split())[:200]
        term = self._cap_ctgov_query_term(term)
        if not term:
            term = "clinical trial"
        return {**base, "query.term": term[:400]}
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call CT.gov v2 using urllib3/requests in a thread (avoids CDN 403 on httpx TLS fingerprints)."""
        await rate_limiter.acquire("clinical_trials")

        ua = (getattr(settings, "CLINICAL_TRIALS_USER_AGENT", None) or "").strip() or _DEFAULT_CT_USER_AGENT
        headers = {
            "User-Agent": ua,
            "Accept": "application/json",
        }
        url = f"{self.base_url}{endpoint}"

        def _sync_get() -> tuple[int, Dict[str, Any]]:
            r = requests.get(url, params=params, headers=headers, timeout=self.request_timeout_sec)
            status = r.status_code
            r.raise_for_status()
            return status, r.json()

        start_time = time.perf_counter()
        try:
            status, data = await asyncio.to_thread(_sync_get)
            elapsed = time.perf_counter() - start_time
            log_api_call("clinical_trials", endpoint, status, elapsed)
            return data
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "?"
            log_error(e, f"ClinicalTrials API error: {code}")
            raise
        except Exception as e:
            log_error(e, "ClinicalTrials API request")
            raise
    
    async def search_studies(self, query: str, max_results: int = 50) -> List[ClinicalTrialResult]:
        """Search for clinical trials using API if available, otherwise AACT database"""
        print(f"🔍 ClinicalTrialsAgent.search_studies called with query: '{query}', max_results: {max_results}")

        # Try API first
        try:
            print(f"📊 Attempting ClinicalTrials.gov API search for: {query}")
            api_results = await self._search_studies_api(query, max_results)
            if api_results:
                return api_results
        except Exception as e:
            log_error(e, f"ClinicalTrials API search failed for query: {query}, falling back to AACT")
            print(f"❌ ClinicalTrials API search failed: {e}")

        # Fallback to AACT database search
        if self.use_aact and aact_agent.enabled:
            try:
                print(f"📊 Attempting AACT database search for: {query}")
                aact_results = await aact_agent.search_studies(query, max_results)
                if aact_results:
                    return aact_results
            except Exception as e:
                log_error(e, f"AACT search failed for query: {query}")
                print(f"❌ AACT search failed: {e}")

        return []
    
    async def _search_studies_api(self, query: str, max_results: int = 50) -> List[ClinicalTrialResult]:
        """Search studies using the ClinicalTrials.gov API"""
        print(f"🔍 ClinicalTrialsAgent._search_studies_api called with query: '{query}'")
        
        normalized_q = self._normalize_search_text(query)
        cache_key = cache_manager.get_api_cache_key(
            "clinical_trials",
            "studies",
            {"query": normalized_q or query, "max_results": max_results},
        )
        
        # Check cache first
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            print(f"📊 Using cached result for query: {query}")
            return cached_result
        
        params = self._studies_list_params(query, max_results)
        
        print(f"📊 Making API request with params: {params}")
        
        try:
            data = await self._make_request(CLINICAL_TRIALS_ENDPOINTS["studies"], params)
            print(f"📊 API response received, studies count: {len(data.get('studies', []))}")
            
            results = []
            for study in data.get("studies", []):
                try:
                    # Extract data from the new nested structure
                    protocol_section = study.get("protocolSection", {})
                    identification = protocol_section.get("identificationModule", {})
                    status = protocol_section.get("statusModule", {})
                    sponsor = protocol_section.get("sponsorCollaboratorsModule", {})
                    description = protocol_section.get("descriptionModule", {})
                    conditions = protocol_section.get("conditionsModule", {})
                    design = protocol_section.get("designModule", {})
                    enrollment = protocol_section.get("designModule", {}).get("enrollmentInfo", {})
                    locations = protocol_section.get("contactsLocationsModule", {}).get("locations", [])
                    
                    # Get lead sponsor name
                    lead_sponsor = sponsor.get("leadSponsor", {})
                    lead_sponsor_name = lead_sponsor.get("name", "")
                    
                    # Get conditions
                    condition_list = conditions.get("conditions", [])
                    condition_text = ", ".join(condition_list) if condition_list else ""
                    
                    # Get interventions
                    interventions = protocol_section.get("armsInterventionsModule", {}).get("interventions", [])
                    intervention_names = []
                    for intervention in interventions:
                        intervention_names.append(intervention.get("name", ""))
                    intervention_text = ", ".join(intervention_names) if intervention_names else ""
                    
                    # Get location
                    location_text = ""
                    if locations:
                        location = locations[0]
                        country = location.get("country", "")
                        city = location.get("city", {}).get("name", "")
                        state = location.get("state", {}).get("name", "")
                        location_parts = [part for part in [city, state, country] if part]
                        location_text = ", ".join(location_parts)
                    
                    # Get dates
                    start_date_struct = status.get("startDateStruct", {})
                    completion_date_struct = status.get("completionDateStruct", {})
                    start_date = start_date_struct.get("date", "")
                    completion_date = completion_date_struct.get("date", "")
                    
                    result = ClinicalTrialResult(
                        nct_id=identification.get("nctId", ""),
                        title=identification.get("briefTitle", ""),
                        condition=condition_text,
                        intervention=intervention_text,
                        sponsor=lead_sponsor_name,
                        status=status.get("overallStatus", ""),
                        phase=", ".join(design.get("phases", [])),
                        enrollment=enrollment.get("count"),
                        start_date=start_date,
                        completion_date=completion_date,
                        description=description.get("briefSummary", ""),
                        location=location_text,
                        relevance_score=0.5  # Will be calculated later
                    )
                    results.append(result)
                except Exception as e:
                    log_error(e, f"Processing study {study.get('protocolSection', {}).get('identificationModule', {}).get('nctId', 'unknown')}")
                    continue
            
            print(f"📊 Successfully processed {len(results)} studies from API")
            
            # Cache results
            cache_manager.set(cache_key, results)
            return results
            
        except Exception as e:
            log_error(e, "ClinicalTrials search")
            print(f"❌ ClinicalTrials API search failed: {e}")
            return []
    
    async def search_by_condition(self, condition: str, max_results: int = 50) -> List[ClinicalTrialResult]:
        """Search trials by medical condition"""
        if self.use_aact and aact_agent.enabled:
            try:
                pat = aact_agent.like_pattern(condition)
                if not pat:
                    return await self._search_by_condition_api(condition, max_results)
                sql_query = """
SELECT DISTINCT ON (s.nct_id)
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
  (SELECT string_agg(DISTINCT c2.name, ', ' ORDER BY c2.name)
   FROM ctgov.conditions c2 WHERE c2.nct_id = s.nct_id) AS condition,
  (SELECT string_agg(DISTINCT i.name, ', ' ORDER BY i.name)
   FROM ctgov.interventions i WHERE i.nct_id = s.nct_id) AS intervention_name,
  (SELECT cf.city FROM ctgov.facilities cf WHERE cf.nct_id = s.nct_id ORDER BY cf.id NULLS LAST LIMIT 1) AS location_city,
  (SELECT cf.state FROM ctgov.facilities cf WHERE cf.nct_id = s.nct_id ORDER BY cf.id NULLS LAST LIMIT 1) AS location_state,
  (SELECT cf.country FROM ctgov.facilities cf WHERE cf.nct_id = s.nct_id ORDER BY cf.id NULLS LAST LIMIT 1) AS location_country
FROM ctgov.studies s
INNER JOIN ctgov.conditions c ON c.nct_id = s.nct_id AND c.name ILIKE $1
LEFT JOIN ctgov.brief_summaries bs ON bs.nct_id = s.nct_id
ORDER BY s.nct_id, s.start_date DESC NULLS LAST
LIMIT $2;
"""
                result = await aact_agent.execute_custom_query(sql_query, [pat, max_results])
                if result["success"]:
                    return await self._convert_aact_results_to_trials(result["results"])
            except Exception as e:
                log_error(e, f"AACT condition search failed for {condition}")
        
        # Fallback to API search
        return await self._search_by_condition_api(condition, max_results)
    
    async def _search_by_condition_api(self, condition: str, max_results: int = 50) -> List[ClinicalTrialResult]:
        """Search trials by condition using API"""
        cache_key = cache_manager.get_api_cache_key("clinical_trials", "condition", {"condition": condition, "max_results": max_results})
        
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        params = {
            "query.cond": condition,
            "pageSize": min(max_results, 100),
            "fields": "NCTId,BriefTitle,Condition,InterventionName,LeadSponsorName,OverallStatus,Phase,EnrollmentCount,StartDate,CompletionDate,BriefSummary,LocationCountry",
            "format": "json"
        }
        
        try:
            data = await self._make_request(CLINICAL_TRIALS_ENDPOINTS["studies"], params)
            results = await self._parse_studies_response(data, max_results)
            cache_manager.set(cache_key, results)
            return results
        except Exception as e:
            log_error(e, f"Condition search for {condition}")
            return []
    
    async def search_by_intervention(self, intervention: str, max_results: int = 50) -> List[ClinicalTrialResult]:
        """Search trials by intervention"""
        if self.use_aact and aact_agent.enabled:
            try:
                pat = aact_agent.like_pattern(intervention)
                if not pat:
                    return await self._search_by_intervention_api(intervention, max_results)
                sql_query = """
SELECT DISTINCT ON (s.nct_id)
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
  (SELECT string_agg(DISTINCT c.name, ', ' ORDER BY c.name)
   FROM ctgov.conditions c WHERE c.nct_id = s.nct_id) AS condition,
  (SELECT string_agg(DISTINCT i2.name, ', ' ORDER BY i2.name)
   FROM ctgov.interventions i2 WHERE i2.nct_id = s.nct_id) AS intervention_name,
  (SELECT f.city FROM ctgov.facilities f WHERE f.nct_id = s.nct_id ORDER BY f.id NULLS LAST LIMIT 1) AS location_city,
  (SELECT f.state FROM ctgov.facilities f WHERE f.nct_id = s.nct_id ORDER BY f.id NULLS LAST LIMIT 1) AS location_state,
  (SELECT f.country FROM ctgov.facilities f WHERE f.nct_id = s.nct_id ORDER BY f.id NULLS LAST LIMIT 1) AS location_country
FROM ctgov.studies s
INNER JOIN ctgov.interventions iv ON iv.nct_id = s.nct_id AND iv.name ILIKE $1
LEFT JOIN ctgov.brief_summaries bs ON bs.nct_id = s.nct_id
ORDER BY s.nct_id, s.start_date DESC NULLS LAST
LIMIT $2;
"""
                result = await aact_agent.execute_custom_query(sql_query, [pat, max_results])
                if result["success"]:
                    return await self._convert_aact_results_to_trials(result["results"])
            except Exception as e:
                log_error(e, f"AACT intervention search failed for {intervention}")
        
        # Fallback to API search
        return await self._search_by_intervention_api(intervention, max_results)
    
    async def _search_by_intervention_api(self, intervention: str, max_results: int = 50) -> List[ClinicalTrialResult]:
        """Search trials by intervention using API"""
        cache_key = cache_manager.get_api_cache_key("clinical_trials", "intervention", {"intervention": intervention, "max_results": max_results})
        
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        params = {
            "query.intr": intervention,
            "pageSize": min(max_results, 100),
            "fields": "NCTId,BriefTitle,Condition,InterventionName,LeadSponsorName,OverallStatus,Phase,EnrollmentCount,StartDate,CompletionDate,BriefSummary,LocationCountry",
            "format": "json"
        }
        
        try:
            data = await self._make_request(CLINICAL_TRIALS_ENDPOINTS["studies"], params)
            results = await self._parse_studies_response(data, max_results)
            cache_manager.set(cache_key, results)
            return results
        except Exception as e:
            log_error(e, f"Intervention search for {intervention}")
            return []
    
    async def search_by_sponsor(self, sponsor: str, max_results: int = 50) -> List[ClinicalTrialResult]:
        """Search trials by sponsor"""
        if self.use_aact and aact_agent.enabled:
            try:
                pat = aact_agent.like_pattern(sponsor)
                if not pat:
                    return await self._search_by_sponsor_api(sponsor, max_results)
                sql_query = """
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
  (SELECT string_agg(DISTINCT c.name, ', ' ORDER BY c.name)
   FROM ctgov.conditions c WHERE c.nct_id = s.nct_id) AS condition,
  (SELECT string_agg(DISTINCT i.name, ', ' ORDER BY i.name)
   FROM ctgov.interventions i WHERE i.nct_id = s.nct_id) AS intervention_name,
  (SELECT f.city FROM ctgov.facilities f WHERE f.nct_id = s.nct_id ORDER BY f.id NULLS LAST LIMIT 1) AS location_city,
  (SELECT f.state FROM ctgov.facilities f WHERE f.nct_id = s.nct_id ORDER BY f.id NULLS LAST LIMIT 1) AS location_state,
  (SELECT f.country FROM ctgov.facilities f WHERE f.nct_id = s.nct_id ORDER BY f.id NULLS LAST LIMIT 1) AS location_country
FROM ctgov.studies s
LEFT JOIN ctgov.brief_summaries bs ON bs.nct_id = s.nct_id
WHERE s.lead_sponsor_name ILIKE $1
ORDER BY s.start_date DESC NULLS LAST
LIMIT $2;
"""
                result = await aact_agent.execute_custom_query(sql_query, [pat, max_results])
                if result["success"]:
                    return await self._convert_aact_results_to_trials(result["results"])
            except Exception as e:
                log_error(e, f"AACT sponsor search failed for {sponsor}")
        
        # Fallback to API search
        return await self._search_by_sponsor_api(sponsor, max_results)
    
    async def _search_by_sponsor_api(self, sponsor: str, max_results: int = 50) -> List[ClinicalTrialResult]:
        """Search trials by sponsor using API"""
        cache_key = cache_manager.get_api_cache_key("clinical_trials", "sponsor", {"sponsor": sponsor, "max_results": max_results})
        
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        params = {
            "query.spons": sponsor,
            "pageSize": min(max_results, 100),
            "fields": "NCTId,BriefTitle,Condition,InterventionName,LeadSponsorName,OverallStatus,Phase,EnrollmentCount,StartDate,CompletionDate,BriefSummary,LocationCountry",
            "format": "json"
        }
        
        try:
            data = await self._make_request(CLINICAL_TRIALS_ENDPOINTS["studies"], params)
            results = await self._parse_studies_response(data, max_results)
            cache_manager.set(cache_key, results)
            return results
        except Exception as e:
            log_error(e, f"Sponsor search for {sponsor}")
            return []
    
    async def _parse_studies_response(self, data: Dict[str, Any], max_results: int) -> List[ClinicalTrialResult]:
        """Parse the studies response from the new API structure"""
        results = []
        for study in data.get("studies", [])[:max_results]:
            try:
                # Extract data from the new nested structure
                protocol_section = study.get("protocolSection", {})
                identification = protocol_section.get("identificationModule", {})
                status = protocol_section.get("statusModule", {})
                sponsor = protocol_section.get("sponsorCollaboratorsModule", {})
                description = protocol_section.get("descriptionModule", {})
                conditions = protocol_section.get("conditionsModule", {})
                design = protocol_section.get("designModule", {})
                enrollment = design.get("enrollmentInfo", {})
                locations = protocol_section.get("contactsLocationsModule", {}).get("locations", [])
                
                # Get lead sponsor name
                lead_sponsor = sponsor.get("leadSponsor", {})
                lead_sponsor_name = lead_sponsor.get("name", "")
                
                # Get conditions
                condition_list = conditions.get("conditions", [])
                condition_text = ", ".join(condition_list) if condition_list else ""
                
                # Get interventions
                interventions = protocol_section.get("armsInterventionsModule", {}).get("interventions", [])
                intervention_names = []
                for intervention in interventions:
                    intervention_names.append(intervention.get("name", ""))
                intervention_text = ", ".join(intervention_names) if intervention_names else ""
                
                # Get location
                location_text = ""
                if locations:
                    location = locations[0]
                    country = location.get("country", "")
                    city = location.get("city", {}).get("name", "")
                    state = location.get("state", {}).get("name", "")
                    location_parts = [part for part in [city, state, country] if part]
                    location_text = ", ".join(location_parts)
                
                # Get dates
                start_date_struct = status.get("startDateStruct", {})
                completion_date_struct = status.get("completionDateStruct", {})
                start_date = start_date_struct.get("date", "")
                completion_date = completion_date_struct.get("date", "")
                
                result = ClinicalTrialResult(
                    nct_id=identification.get("nctId", ""),
                    title=identification.get("briefTitle", ""),
                    condition=condition_text,
                    intervention=intervention_text,
                    sponsor=lead_sponsor_name,
                    status=status.get("overallStatus", ""),
                    phase=", ".join(design.get("phases", [])),
                    enrollment=enrollment.get("count"),
                    start_date=start_date,
                    completion_date=completion_date,
                    description=description.get("briefSummary", ""),
                    location=location_text,
                    relevance_score=0.5
                )
                results.append(result)
            except Exception as e:
                log_error(e, f"Processing study {study.get('protocolSection', {}).get('identificationModule', {}).get('nctId', 'unknown')}")
                continue
        
        return results
    
    async def get_study_details(self, nct_id: str) -> Optional[ClinicalTrialResult]:
        """Get detailed information about a specific study"""
        if self.use_aact and aact_agent.enabled:
            try:
                # Try AACT database first for comprehensive details
                aact_result = await aact_agent.get_study_details(nct_id)
                if aact_result:
                    return aact_result
            except Exception as e:
                log_error(e, f"AACT get study details failed for {nct_id}")
        
        # Fallback to API
        return await self._get_study_details_api(nct_id)
    
    async def _get_study_details_api(self, nct_id: str) -> Optional[ClinicalTrialResult]:
        """Get study details using API"""
        cache_key = cache_manager.get_api_cache_key("clinical_trials", "study_details", {"nct_id": nct_id})
        
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        params = {
            "query.id": nct_id,
            "fields": "NCTId,BriefTitle,OfficialTitle,Condition,InterventionName,LeadSponsorName,OverallStatus,Phase,EnrollmentCount,StartDate,CompletionDate,BriefSummary,DetailedDescription,LocationCountry,LocationFacility",
            "format": "json"
        }
        
        try:
            data = await self._make_request(CLINICAL_TRIALS_ENDPOINTS["studies"], params)
            
            if data.get("studies"):
                study = data["studies"][0]
                results = await self._parse_studies_response({"studies": [study]}, 1)
                
                if results:
                    result = results[0]
                    cache_manager.set(cache_key, result)
                    return result
            
            return None
            
        except Exception as e:
            log_error(e, f"Get study details for {nct_id}")
            return None
    
    async def _convert_aact_results_to_trials(self, aact_results: List[Dict[str, Any]]) -> List[ClinicalTrialResult]:
        """Convert AACT database results to ClinicalTrialResult objects"""
        trials = []
        for row in aact_results:
            try:
                # Build location string
                location_parts = []
                if row.get('location_city'):
                    location_parts.append(row['location_city'])
                if row.get('location_state'):
                    location_parts.append(row['location_state'])
                if row.get('location_country'):
                    location_parts.append(row['location_country'])
                location = ", ".join(location_parts) if location_parts else ""
                
                enr = row.get("enrollment")
                if enr is not None:
                    try:
                        enr = int(enr)
                    except (TypeError, ValueError):
                        enr = None

                trial = ClinicalTrialResult(
                    nct_id=row['nct_id'],
                    title=row.get('brief_title') or row.get('official_title') or "",
                    condition=row.get('condition', ''),
                    intervention=row.get('intervention_name', ''),
                    sponsor=row.get('lead_sponsor_name', ''),
                    status=row.get('overall_status', ''),
                    phase=row.get('phase', ''),
                    enrollment=enr,
                    start_date=str(row['start_date']) if row.get('start_date') else '',
                    completion_date=str(row['completion_date']) if row.get('completion_date') else '',
                    description=row.get('brief_summary', ''),
                    location=location,
                    relevance_score=0.8
                )
                trials.append(trial)
            except Exception as e:
                log_error(e, f"Converting AACT result to trial: {row.get('nct_id', 'unknown')}")
                continue
        
        return trials
    
    async def search_recent_trials(self, days: int = 30, max_results: int = 50) -> List[ClinicalTrialResult]:
        """Search for recently updated trials"""
        if self.use_aact and aact_agent.enabled:
            try:
                return await aact_agent.search_recent_updated(days, max_results)
            except Exception as e:
                log_error(e, f"AACT recent trials search failed for {days} days")
        
        # Fallback to API search
        return await self._search_recent_trials_api(days, max_results)
    
    async def _search_recent_trials_api(self, days: int = 30, max_results: int = 50) -> List[ClinicalTrialResult]:
        """Search recent trials using API"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Use the advanced query format for date ranges
        date_query = f"AREA[LastUpdatePostDate]RANGE[{start_date.strftime('%Y-%m-%d')},MAX]"
        
        params = {
            "query.term": date_query,
            "pageSize": min(max_results, 100),
            "fields": "NCTId,BriefTitle,Condition,InterventionName,LeadSponsorName,OverallStatus,Phase,EnrollmentCount,StartDate,CompletionDate,BriefSummary,LocationCountry",
            "format": "json"
        }
        
        try:
            data = await self._make_request(CLINICAL_TRIALS_ENDPOINTS["studies"], params)
            return await self._parse_studies_response(data, max_results)
        except Exception as e:
            log_error(e, f"Recent trials search for {days} days")
            return []
    
    async def get_database_statistics(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        if self.use_aact and aact_agent.enabled:
            try:
                return await aact_agent.get_study_statistics()
            except Exception as e:
                log_error(e, "AACT get statistics")
        
        return {"error": "Statistics not available without AACT database"}

# Global ClinicalTrials agent instance
clinical_trials_agent = ClinicalTrialsAgent() 