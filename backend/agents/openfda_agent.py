"""
OpenFDA API Agent
"""
import asyncio
import httpx
from typing import List, Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from config import settings, OPENFDA_ENDPOINTS
from utils.logger import log_api_call, log_error
from utils.cache import cache_manager
from utils.rate_limiter import rate_limiter
from models.schemas import OpenFDAResult
from agents.llm_agent import llm_agent
from datetime import datetime
import json
import re

# openFDA returns HTTP 404 with NOT_FOUND when a search matches zero records (not a client failure).
# See https://open.fda.gov/apis/ — empty result sets use this response shape.


def _openfda_retry_predicate(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        if code == 404:
            return False
        if code == 400:
            return False
        return code >= 500
    return isinstance(exc, (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout))


class OpenFDAAgent:
    # LLM / planner output → ordered query strategies for Drugs@FDA (open.fda.gov/apis/drug/drugsfda/).
    _PLAN_INTENTS = frozenset({
        "drug_substance",
        "brand",
        "company",
        "application",
        "pharm_class",
        "form_route",
        "general",
    })

    # Tokens that are not useful as Drugs@FDA search terms (often leaked from error text or generic fallbacks).
    _OPENFDA_NOISE_TOKENS = frozenset({
        "error", "errors", "generating", "response", "invalid", "none", "null",
        "the", "and", "for", "with", "from", "this", "that", "query", "search",
        "result", "results", "message", "code", "type", "details",
    })

    def __init__(self):
        self.base_url = settings.OPENFDA_BASE_URL
        self.api_key = settings.OPENFDA_API_KEY
        self.timeout = httpx.Timeout(15.0)

    @staticmethod
    def _escape_openfda_term(term: str) -> str:
        """Strip characters that break openFDA query strings."""
        return re.sub(r'["\\\n\r\t]', " ", term).strip()

    @staticmethod
    def _split_or_phrases(query: str) -> List[str]:
        """Split LLM output like 'a OR b' into distinct phrases."""
        parts = re.split(r"\s+(?:OR|or)\s+", query.strip())
        out: List[str] = []
        for p in parts:
            p = re.sub(r"\s+", " ", p.strip())
            if p and p.lower() != "or":
                out.append(p)
        return out

    def _sanitize_openfda_query(self, query: str) -> str:
        """
        Reject upstream/LLM garbage (error blobs, JSON, URLs) that cause useless requests and 500 parse errors.
        """
        if not query:
            return ""
        q = re.sub(r"\s+", " ", query.strip())
        if len(q) > 220:
            q = q[:220].rsplit(" ", 1)[0]
        low = q.lower()
        junk_markers = (
            "error generating",
            "invalid_request",
            "api usage limits",
            "workspace api",
            "request_id",
            "parse_exception",
            "server_error",
            "traceback",
            "http://",
            "https://",
        )
        if any(m in low for m in junk_markers):
            return ""
        if q.startswith("{") or "': {'" in q or "'type':" in low:
            return ""
        return q

    @staticmethod
    def _dedupe_strategies(strategies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen: set = set()
        out: List[Dict[str, Any]] = []
        for p in strategies:
            key = (p.get("search", ""), p.get("limit"))
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
        return out

    def _collect_openfda_tokens(self, query: str) -> List[str]:
        """Split sanitized query into 1–3 tokens (handles LLM 'a OR b' and multi-word phrases)."""
        collected: List[str] = []
        for phrase in self._split_or_phrases(query)[:3]:
            phrase = phrase.strip()
            phrase = re.sub(r"(?i)^openfda\.\w+:\s*", "", phrase)
            phrase = self._escape_openfda_term(phrase)
            if not phrase or len(phrase) < 2:
                continue
            subtoks = [t for t in re.split(r"[\s,/]+", phrase) if t]
            if len(subtoks) == 1:
                t = subtoks[0]
                if len(t) >= 3 and t.lower() not in self._OPENFDA_NOISE_TOKENS:
                    collected.append(t)
            else:
                for t in subtoks:
                    if len(t) >= 3 and t.lower() not in self._OPENFDA_NOISE_TOKENS:
                        collected.append(t)
        seen: set = set()
        out: List[str] = []
        for t in collected:
            k = t.lower()
            if k in seen:
                continue
            seen.add(k)
            out.append(t)
            if len(out) >= 3:
                break
        return out

    def _openfda_name_or_clause(self, tok: str) -> str:
        """Single OR group across generic / brand / substance for one token (one + chain = OR in openFDA)."""
        et = self._escape_openfda_term(tok)
        if len(et) < 2:
            return ""
        return f'openfda.generic_name:"{et}"+openfda.brand_name:"{et}"+openfda.substance_name:"{et}"'

    @staticmethod
    def _looks_like_fielded_openfda_query(q: str) -> bool:
        """True if the string is already a Drugs@FDA search expression (not natural language)."""
        if not q or q.count(":") < 1:
            return False
        return bool(
            re.search(
                r"(?:\b(?:openfda|products)\.[a-z_0-9]+:|(?:^|[\s+])(?:application_number|sponsor_name):)",
                q,
                re.I,
            )
        )

    def _heuristic_search_plan(self, query: str) -> Optional[Dict[str, Any]]:
        """Fast path: NDA/ANDA/BLA numbers and obvious application references (no LLM)."""
        q = (query or "").strip()
        if not q:
            return None
        m = re.search(r"\b(NDA|ANDA|BLA)\s*-?\s*(\d{4,})\b", q, re.I)
        if m:
            prefix, digits = m.group(1).upper(), m.group(2)
            return {"intent": "application", "application_number": f"{prefix}{digits}", "terms": []}
        m = re.search(
            r"\bapplication\s*(?:#|number|no\.?)?\s*:?\s*(NDA|ANDA|BLA)\s*-?\s*(\d+)",
            q,
            re.I,
        )
        if m:
            prefix, digits = m.group(1).upper(), m.group(2)
            return {"intent": "application", "application_number": f"{prefix}{digits}", "terms": []}
        return None

    @staticmethod
    def _parse_llm_json_plan(text: str) -> Optional[Dict[str, Any]]:
        raw = (text or "").strip()
        if not raw:
            return None
        if raw.startswith("```"):
            lines = raw.split("\n")
            inner = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            raw = inner.strip()
            if raw.lower().startswith("json"):
                raw = raw[4:].lstrip()
        try:
            obj = json.loads(raw)
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            pass
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            try:
                obj = json.loads(raw[start : end + 1])
                return obj if isinstance(obj, dict) else None
            except json.JSONDecodeError:
                return None
        return None

    def _normalize_plan(self, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Coerce LLM JSON into a stable plan shape."""
        out: Dict[str, Any] = {
            "intent": "general",
            "terms": [],
            "application_number": None,
            "dosage_form": None,
            "route": None,
        }
        if not data:
            return out
        intent = str(data.get("intent") or "general").strip().lower()
        if intent not in self._PLAN_INTENTS:
            intent = "general"
        out["intent"] = intent

        terms_raw = data.get("terms")
        terms: List[str] = []
        if isinstance(terms_raw, list):
            for t in terms_raw:
                if isinstance(t, str) and t.strip():
                    terms.append(re.sub(r"\s+", " ", t.strip()))
        elif isinstance(terms_raw, str) and terms_raw.strip():
            for p in self._split_or_phrases(terms_raw):
                if p.strip():
                    terms.append(re.sub(r"\s+", " ", p.strip()))

        seen: set = set()
        clean_terms: List[str] = []
        for t in terms:
            tl = t.lower()
            if tl in seen:
                continue
            seen.add(tl)
            clean_terms.append(t)
            if len(clean_terms) >= 4:
                break
        out["terms"] = clean_terms

        for key in ("application_number", "dosage_form", "route"):
            v = data.get(key)
            if isinstance(v, str) and v.strip():
                out[key] = re.sub(r"\s+", " ", v.strip())
        return out

    def _plan_terms_for_search(self, plan: Dict[str, Any], fallback_phrase: str) -> List[str]:
        terms = [t for t in (plan.get("terms") or []) if isinstance(t, str) and t.strip()]
        if terms:
            out: List[str] = []
            seen: set = set()
            for t in terms:
                et = self._escape_openfda_term(t)
                if len(et) < 2 or et.lower() in self._OPENFDA_NOISE_TOKENS:
                    continue
                k = et.lower()
                if k in seen:
                    continue
                seen.add(k)
                out.append(et)
                if len(out) >= 4:
                    break
            if out:
                return out
        if plan.get("application_number"):
            return []
        fb = self._sanitize_openfda_query(fallback_phrase)
        if not fb:
            return []
        return self._collect_openfda_tokens(fb) or ([self._escape_openfda_term(fb)] if len(self._escape_openfda_term(fb)) >= 2 else [])

    def _condition_hint_strategies(self, qlow: str, lim: int) -> List[Dict[str, Any]]:
        """Shared biomedical hints (OR-chained, one request each)."""
        s: List[Dict[str, Any]] = []
        if any(x in qlow for x in ("glp-1", "glp1", "glp 1")):
            s.append({
                "search": (
                    'openfda.pharm_class_moa:"Glucagon-Like Peptide-1 Receptor Agonists [MoA]"'
                    '+openfda.pharm_class_epc:"Glucagon-Like Peptide-1 Receptor Agonists [EPC]"'
                ),
                "limit": lim,
            })
        if "oral" in qlow:
            s.append({"search": 'products.route:"ORAL"', "limit": lim})
        if any(c in qlow for c in ("diabetes", "diabetic")):
            s.append({"search": "diabetic+insulin+sulfonylurea", "limit": lim})
        if any(c in qlow for c in ("cancer", "oncology", "tumor")):
            s.append({"search": 'antineoplastic+immunotherapy+"Tumor Necrosis Factor"', "limit": lim})
        if any(c in qlow for c in ("hypertension", "blood pressure")):
            s.append({
                "search": 'antihypertensive+diuretic+"beta blocker"+"calcium channel"',
                "limit": lim,
            })
        if any(c in qlow for c in ("antibiotic", "infection")):
            s.append({"search": "antibiotic+antimicrobial+penicillin", "limit": lim})
        if any(c in qlow for c in ("pain", "analgesic")):
            s.append({"search": "analgesic+opioid+nonsteroidal", "limit": lim})
        return s

    def _build_strategies_from_plan(
        self,
        plan: Dict[str, Any],
        sanitized_query: str,
        lim: int,
    ) -> List[Dict[str, Any]]:
        """Map intent + terms to field-aware openFDA search strings (https://open.fda.gov/apis/query-syntax/)."""
        strategies: List[Dict[str, Any]] = []
        qlow = sanitized_query.lower()
        terms = self._plan_terms_for_search(plan, sanitized_query)

        app = plan.get("application_number")
        application_only = False
        if isinstance(app, str) and app.strip():
            ap = self._escape_openfda_term(app.strip())
            if ap:
                strategies.append({"search": f'application_number:"{ap}"', "limit": lim})
                application_only = (plan.get("intent") or "general") == "application"

        intent = plan.get("intent") or "general"

        if intent == "company":
            for t in terms[:2]:
                strategies.append({
                    "search": f'sponsor_name:"{t}"+openfda.manufacturer_name:"{t}"',
                    "limit": lim,
                })
            for t in terms[:2]:
                c = self._openfda_name_or_clause(t)
                if c:
                    strategies.append({"search": c, "limit": lim})
        elif intent == "brand":
            for t in terms[:2]:
                strategies.append({
                    "search": f'openfda.brand_name:"{t}"+openfda.generic_name:"{t}"+openfda.substance_name:"{t}"',
                    "limit": lim,
                })
        elif intent == "drug_substance":
            name_clauses = [c for c in (self._openfda_name_or_clause(t) for t in terms[:2]) if c]
            if name_clauses:
                strategies.append({"search": "+".join(name_clauses), "limit": lim})
        elif intent == "pharm_class":
            for t in terms[:2]:
                strategies.append({
                    "search": (
                        f'openfda.pharm_class_epc:"{t}"+openfda.pharm_class_moa:"{t}"'
                        f'+openfda.pharm_class_pe:"{t}"'
                    ),
                    "limit": lim,
                })
            name_clauses = [c for c in (self._openfda_name_or_clause(t) for t in terms[:2]) if c]
            if name_clauses:
                strategies.append({"search": "+".join(name_clauses), "limit": lim})
        elif intent == "form_route":
            df = plan.get("dosage_form")
            rt = plan.get("route")
            if isinstance(df, str) and df.strip():
                et = self._escape_openfda_term(df.strip())
                if len(et) >= 2:
                    strategies.append({"search": f'products.dosage_form:"{et}"', "limit": lim})
            if isinstance(rt, str) and rt.strip():
                et = self._escape_openfda_term(rt.strip()).upper()
                if len(et) >= 2:
                    strategies.append({"search": f'products.route:"{et}"', "limit": lim})
            name_clauses = [c for c in (self._openfda_name_or_clause(t) for t in terms[:2]) if c]
            if name_clauses:
                strategies.append({"search": "+".join(name_clauses), "limit": lim})
        else:
            # general (and application-only already handled)
            name_clauses = [c for c in (self._openfda_name_or_clause(t) for t in terms[:2]) if c]
            if name_clauses:
                strategies.append({"search": "+".join(name_clauses), "limit": lim})

        if not application_only:
            if " " in sanitized_query:
                pq = self._escape_openfda_term(sanitized_query)
                if len(pq) >= 3:
                    strategies.append({"search": f'"{pq}"', "limit": lim})

            if sanitized_query:
                strategies.append({"search": sanitized_query, "limit": lim})

            if intent == "company" or any(
                x in qlow
                for x in (
                    "lilly",
                    "pfizer",
                    "novartis",
                    "merck",
                    "roche",
                    "sandoz",
                    "amgen",
                    "gsk",
                    "astrazeneca",
                    "sanofi",
                    "bristol",
                    "vertex",
                    "gilead",
                    "biogen",
                )
            ):
                sq = self._escape_openfda_term(sanitized_query)
                if len(sq) >= 3:
                    strategies.append({"search": f'sponsor_name:"{sq}"', "limit": lim})

            strategies.extend(self._condition_hint_strategies(qlow, lim))
        return self._dedupe_strategies(strategies)

    async def _llm_search_plan(self, user_query: str, *, alternative: bool) -> Dict[str, Any]:
        current_date = datetime.now().strftime("%Y-%m-%d")
        if alternative:
            task = (
                "The last Drugs@FDA search returned no rows. Propose a broader or alternate plan "
                "(different spellings, generic name if brand failed, or pharmacologic class)."
            )
        else:
            task = (
                "Design a concise search plan for the openFDA Drugs@FDA endpoint only "
                "(/drug/drugsfda.json). Use intent to choose fields; put drug/company tokens in `terms`."
            )
        prompt = f"""{task}

CURRENT_DATE: {current_date}
USER_QUERY: {user_query}

Drugs@FDA searchable ideas (harmonized openfda.* on applications):
- application_number (e.g. NDA021920, ANDA077890, BLA125577)
- sponsor_name, openfda.manufacturer_name
- openfda.brand_name, openfda.generic_name, openfda.substance_name
- openfda.pharm_class_epc, openfda.pharm_class_moa, openfda.pharm_class_pe
- products.dosage_form, products.route, products.marketing_status

intent must be one of: drug_substance | brand | company | application | pharm_class | form_route | general

Return ONLY valid JSON (no markdown), shape:
{{
  "intent": "drug_substance",
  "terms": ["lowercase or proper tokens, max 3"],
  "application_number": null,
  "dosage_form": null,
  "route": null
}}

Rules:
- If the user gives NDA/ANDA/BLA + number, intent=application and set application_number to the full id (e.g. NDA214766).
- INN/generic monoclonal names (*mab, *nib, *vir): intent=drug_substance.
- Proprietary / trade names only: intent=brand.
- Sponsor / pharma company only: intent=company; terms = company name tokens.
- Tablet/capsule/injection/oral/IV without a drug name: intent=form_route; set dosage_form or route when obvious else terms describe the form.
- Class questions (SGLT2, GLP-1, beta blocker): intent=pharm_class or drug_substance with class tokens.
- Otherwise intent=general; terms = strongest 1-3 entities (not whole question prose).
"""
        response = await llm_agent.generate_response(prompt)
        parsed = self._parse_llm_json_plan(response)
        return self._normalize_plan(parsed)

    async def _resolve_search_plan(self, user_query: str) -> Dict[str, Any]:
        h = self._heuristic_search_plan(user_query)
        if h:
            return self._normalize_plan(h)
        try:
            plan = await self._llm_search_plan(user_query, alternative=False)
            if not plan.get("terms") and not plan.get("application_number"):
                fb = self._sanitize_openfda_query(await self._extract_search_terms(user_query))
                if fb:
                    plan["terms"] = self._collect_openfda_tokens(fb) or [fb]
                    plan["intent"] = plan.get("intent") or "general"
            return self._normalize_plan(plan)
        except Exception as e:
            print(f"⚠️ Search plan LLM failed: {e}, using heuristic fallback")
            fb = self._sanitize_openfda_query(self._fallback_extract_search_terms(user_query))
            return self._normalize_plan({"intent": "general", "terms": [fb] if fb else []})

    async def _resolve_alternative_plan(self, user_query: str, prior_plan: Dict[str, Any]) -> Dict[str, Any]:
        try:
            plan = await self._llm_search_plan(user_query, alternative=True)
            if plan == self._normalize_plan(prior_plan):
                broader = list(prior_plan.get("terms") or [])
                if broader:
                    plan["terms"] = broader[:1]
                plan["intent"] = "general"
            if not plan.get("terms") and not plan.get("application_number"):
                fb = self._sanitize_openfda_query(await self._extract_search_terms(user_query))
                if fb:
                    plan["terms"] = self._collect_openfda_tokens(fb) or [fb]
            return self._normalize_plan(plan)
        except Exception as e:
            print(f"⚠️ Alternative plan LLM failed: {e}")
            return self._normalize_plan(
                {"intent": "general", "terms": [self._fallback_get_alternative_search_terms(user_query)]}
            )

    @staticmethod
    def _plan_cache_key(plan: Optional[Dict[str, Any]], sanitized_query: str, max_results: int) -> str:
        p = json.dumps(plan or {}, sort_keys=True, default=str)
        return f"openfda_drugs:{max_results}:{p}:{sanitized_query}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception(_openfda_retry_predicate),
        reraise=True,
    )
    async def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make API request with retry logic (5xx / network only; 404 empty hits are not errors)."""
        await rate_limiter.acquire("openfda")

        if self.api_key:
            params = {**params, "api_key": self.api_key}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            start_time = asyncio.get_event_loop().time()

            try:
                url = f"{self.base_url}{endpoint}"
                response = await client.get(url, params=params)
                end_time = asyncio.get_event_loop().time()
                log_api_call("openfda", endpoint, response.status_code, end_time - start_time)

                if response.status_code == 404:
                    try:
                        body = response.json()
                        err = body.get("error") or {}
                        code = err.get("code")
                        msg = str(err.get("message", ""))
                        if code == "NOT_FOUND" or "no matches" in msg.lower():
                            return {"results": []}
                    except Exception:
                        pass

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                error_detail = f"OpenFDA API error: {e.response.status_code}"
                try:
                    error_body = e.response.json()
                    error_detail += f" - {error_body}"
                except Exception:
                    error_detail += f" - {e.response.text[:200]}"
                log_error(e, error_detail)
                raise
            except Exception as e:
                log_error(e, "OpenFDA API request")
                raise
    
    async def search_drugs(self, query: str, max_results: int = 50) -> List[OpenFDAResult]:
        """Search OpenFDA for drug information"""

        
        try:
            plan = await self._resolve_search_plan(query)
            sanitized = self._sanitize_openfda_query(re.sub(r"\s+", " ", (query or "").strip()))
            if not sanitized and (plan.get("terms") or plan.get("application_number")):
                sanitized = " ".join(plan.get("terms") or []) or str(plan.get("application_number") or "")
            cache_label = self._plan_cache_key(plan, sanitized, max_results)

            results = await self._search_openfda_drugs(cache_label, max_results, plan=plan, sanitized_query=sanitized)
            
            if not results:
                print("⚠️ Primary search returned no results, trying alternative search plan")
                alt_plan = await self._resolve_alternative_plan(query, plan)
                alt_label = self._plan_cache_key(alt_plan, sanitized, max_results)
                if alt_label != cache_label:
                    print(f"🔄 Trying alternative plan: intent={alt_plan.get('intent')} terms={alt_plan.get('terms')}")
                    results = await self._search_openfda_drugs(alt_label, max_results, plan=alt_plan, sanitized_query=sanitized)
            
            if not results:
                print("❌ OpenFDA search returned no results after trying alternatives")
                return []
            
    
            return results
            
        except Exception as e:
            print(f"❌ OpenFDA search error: {e}")
            log_error(e, "OpenFDA search")
            return []
    
    async def _extract_search_terms(self, query: str) -> str:
        """Transform complex queries into OpenFDA-compatible search terms using LLM"""
        try:
            # Get current date for context
            current_date = datetime.now().strftime('%Y-%m-%d')
            
            # Use LLM to intelligently extract search terms
            prompt = f"""
You are an expert at searching the FDA drug database. Given a user query, extract the most relevant search terms that would find the drugs they're looking for.

CURRENT DATE: {current_date}

USER QUERY: {query}

TASK: Extract 1-3 specific search terms that would be most effective for finding relevant drugs in the FDA database.

DATE CONTEXT:
- When the query mentions "latest", "recent", "new", or similar terms, consider the current date above
- "Latest" typically means within the last 6-12 months from the current date
- "Recent" typically means within the last 1-2 years from the current date
- "New" typically means within the last 1-3 months from the current date

AVAILABLE SEARCH FIELDS (based on OpenFDA schema):
- openfda.brand_name: Brand/trade names (e.g., "Advil", "Tylenol")
- openfda.generic_name: Generic names (e.g., "ibuprofen", "acetaminophen")
- openfda.substance_name: Active ingredients (e.g., "aspirin", "metformin")
- openfda.pharm_class_epc: Established pharmacologic class (e.g., "Thiazide Diuretic [EPC]", "Tumor Necrosis Factor Blocker [EPC]")
- openfda.pharm_class_moa: Mechanism of action (e.g., "Calcium Channel Antagonists [MoA]", "Tumor Necrosis Factor Receptor Blocking Activity [MoA]")
- openfda.pharm_class_pe: Physiologic effect (e.g., "Increased Diuresis [PE]", "Decreased Cytokine Activity [PE]")
- openfda.pharm_class_cs: Chemical structure (e.g., "Thiazides [Chemical/Ingredient]", "Antibodies, Monoclonal [Chemical/Ingredient]")
- products.dosage_form: Dosage form (e.g., "tablet", "solution for injection")
- products.route: Route of administration (e.g., "oral", "intravenous")
- products.marketing_status: Marketing status (e.g., "Prescription", "Over-the-counter")
- sponsor_name: Company that submitted the application

IMPORTANT RULES:
1. For medical conditions, prefer specific drug classes, mechanisms, or known drug names over the condition itself
2. For company names, use just the company name without field prefixes (e.g., "eli lilly" not "sponsor_name:eli lilly")
3. For drug names, use just the drug name (e.g., "nivolumab" not "openfda.generic_name:nivolumab")
4. Keep search terms simple and avoid complex field syntax
5. Consider temporal context when the query mentions recent/latest/new

EXAMPLES:
- "What are the latest FDA approved drugs for diabetes?" → "antidiabetic OR metformin OR insulin OR sulfonylurea"
- "Find information about nivolumab and its FDA approval status" → "nivolumab"
- "What are the side effects of aspirin according to FDA data?" → "aspirin"
- "Compare pembrolizumab and nivolumab FDA approvals" → "pembrolizumab"
- "What drugs are available in tablet form for pain management?" → "tablet"
- "Show me all immunotherapy drugs approved by the FDA" → "immunotherapy OR Tumor Necrosis Factor Blocker"
- "What antibiotics are available for treating infections?" → "antibiotic OR antimicrobial"
- "Find antihypertensive medications" → "antihypertensive OR diuretic OR beta blocker"
- "What was the latest drug that Eli Lilly got approval for?" → "eli lilly OR lilly"

Return ONLY the search term(s) separated by spaces, nothing else:
"""
            
            response = await llm_agent.generate_response(prompt)
            
            # Clean up the response
            search_terms = response.strip().lower()
            
            # Remove any markdown formatting or extra text
            if search_terms.startswith('```'):
                search_terms = search_terms.split('\n')[1] if len(search_terms.split('\n')) > 1 else search_terms
            if search_terms.endswith('```'):
                search_terms = search_terms[:-3]
            
            # Normalize whitespace and strip newlines/tabs
            search_terms = re.sub(r"\s+", " ", search_terms.strip())
            

            
            return search_terms if search_terms else "drug"
            
        except Exception as e:
            print(f"⚠️ LLM search term extraction failed: {e}, using fallback")
            # Fallback to simple extraction
            return self._fallback_extract_search_terms(query)
    
    def _fallback_extract_search_terms(self, query: str) -> str:
        """Fallback method for extracting search terms when LLM fails"""
        query_lower = query.lower()
        
        # Remove common question words and non-searchable terms
        stop_words = {
            'what', 'when', 'where', 'which', 'about', 'between', 'latest', 'recent', 
            'approved', 'fda', 'drugs', 'medications', 'information', 'data', 'find',
            'search', 'look', 'get', 'show', 'tell', 'provide', 'give', 'list'
        }
        
        # Extract medical/drug terms that are likely to be in the OpenFDA database
        medical_terms = [
            # Common drug names
            "aspirin", "ibuprofen", "acetaminophen", "metformin", "insulin", 
            "warfarin", "amoxicillin", "lisinopril", "atorvastatin", "omeprazole",
            "albuterol", "prednisone", "hydrocodone", "nivolumab", "pembrolizumab",
            
            # Medical conditions
            "diabetes", "cancer", "hypertension", "asthma", "depression", "anxiety",
            "arthritis", "migraine", "epilepsy", "parkinson", "alzheimer",
            
            # Drug classes
            "antibiotic", "analgesic", "antidepressant", "antihypertensive",
            "immunotherapy", "chemotherapy", "vaccine", "hormone",
            
            # Dosage forms
            "tablet", "capsule", "injection", "cream", "ointment", "liquid", "suspension",
            
            # Routes of administration
            "oral", "intravenous", "topical", "inhalation", "subcutaneous"
        ]
        
        # Find medical terms in the query
        found_terms = []
        for term in medical_terms:
            if term in query_lower:
                found_terms.append(term)
        
        # If we found specific medical terms, use them
        if found_terms:
            # Prioritize drug names over conditions, and conditions over forms/routes
            drug_names = ["aspirin", "ibuprofen", "acetaminophen", "metformin", "insulin", 
                         "warfarin", "amoxicillin", "lisinopril", "atorvastatin", "omeprazole",
                         "albuterol", "prednisone", "hydrocodone", "nivolumab", "pembrolizumab"]
            
            # Check for drug names first
            for drug in drug_names:
                if drug in query_lower:
                    return drug
            
            # Then check for conditions
            conditions = ["diabetes", "cancer", "hypertension", "asthma", "depression", "anxiety"]
            for condition in conditions:
                if condition in query_lower:
                    return condition
            
            # Then check for drug classes
            drug_classes = ["antibiotic", "analgesic", "antidepressant", "antihypertensive", "immunotherapy"]
            for drug_class in drug_classes:
                if drug_class in query_lower:
                    return drug_class
            
            # Return the first found term
            return found_terms[0]
        
        # If no medical terms found, extract meaningful words
        words = query.split()
        meaningful_words = []
        
        for word in words:
            word_clean = word.lower().strip('.,!?;:')
            if (len(word_clean) > 3 and 
                word_clean not in stop_words and
                not word_clean.isdigit()):
                meaningful_words.append(word_clean)
        
        if meaningful_words:
            # Limit to 2-3 most relevant words
            return " ".join(meaningful_words[:2])
        
        # Last resort: use first few non-stop words
        words = [w.lower().strip('.,!?;:') for w in query.split() if w.lower().strip('.,!?;:') not in stop_words]
        return " ".join(words[:3]) if words else "drug"
    
    def _fallback_get_alternative_search_terms(self, query: str) -> str:
        """Fallback method for alternative search terms when LLM fails"""
        query_lower = query.lower()
        
        # Try to extract any medical condition or drug class mentioned
        medical_terms = [
            "diabetes", "cancer", "hypertension", "asthma", "depression", "anxiety",
            "arthritis", "migraine", "epilepsy", "parkinson", "alzheimer",
            "antibiotic", "analgesic", "antidepressant", "antihypertensive",
            "immunotherapy", "chemotherapy", "vaccine", "hormone"
        ]
        
        for term in medical_terms:
            if term in query_lower:
                return term
        
        # If no medical terms found, try common drug names
        common_drugs = ["aspirin", "ibuprofen", "metformin", "insulin"]
        for drug in common_drugs:
            if drug in query_lower:
                return drug
        
        # Default fallback to a general search
        return "drug"
    
    async def _search_openfda_drugs(
        self,
        cache_key: str,
        max_results: int,
        *,
        plan: Optional[Dict[str, Any]] = None,
        sanitized_query: Optional[str] = None,
        fielded_search: Optional[str] = None,
    ) -> List[OpenFDAResult]:
        """Execute Drugs@FDA search strategies (404 NOT_FOUND = empty; OR via + per open.fda.gov/apis/query-syntax/)."""
        if fielded_search is not None:
            fs = re.sub(r"\s+", " ", (fielded_search or "").strip())
            if not fs:
                return []
            print(f"🔍 Searching OpenFDA (fielded): '{fs[:120]}...'" if len(fs) > 120 else f"🔍 Searching OpenFDA (fielded): '{fs}'")
            cache_key = f"openfda_drugs:{max_results}:fielded:{fs}"
            cached_result = cache_manager.get(cache_key)
            if cached_result:
                print("✅ Returning cached OpenFDA results")
                return [OpenFDAResult(**item) for item in cached_result]
            lim = min(max_results, 99)
            search_strategies = [{"search": fs, "limit": lim}]
        else:
            sq = re.sub(r"\s+", " ", (sanitized_query or "").strip())
            sq = self._sanitize_openfda_query(sq)
            if not sq and not (plan and (plan.get("terms") or plan.get("application_number"))):
                print("❌ Empty or unusable OpenFDA query after sanitization")
                return []

            display = sq or " ".join(plan.get("terms") or []) or str(plan.get("application_number") or "")
            print(f"🔍 Searching OpenFDA (plan={plan.get('intent') if plan else 'n/a'}): '{display[:120]}...'" if len(display) > 120 else f"🔍 Searching OpenFDA (plan={plan.get('intent') if plan else 'n/a'}): '{display}'")

            cached_result = cache_manager.get(cache_key)
            if cached_result:
                print("✅ Returning cached OpenFDA results")
                return [OpenFDAResult(**item) for item in cached_result]

            lim = min(max_results, 99)
            if sq and self._looks_like_fielded_openfda_query(sq):
                search_strategies = [{"search": sq, "limit": lim}]
            elif plan is not None:
                search_strategies = self._build_strategies_from_plan(plan, sq, lim)
            else:
                pl = self._normalize_plan(
                    {
                        "intent": "general",
                        "terms": self._collect_openfda_tokens(sq) or ([sq] if len(sq) >= 2 else []),
                    }
                )
                search_strategies = self._build_strategies_from_plan(pl, sq, lim)

        if not search_strategies:
            return []

        for params in search_strategies:
            try:
                response = await self._make_request(OPENFDA_ENDPOINTS["drugs"], params)
                results: List[OpenFDAResult] = []
                for item in response.get("results") or []:
                    try:
                        parsed = self._parse_drug_result(item)
                        if parsed:
                            results.append(parsed)
                    except Exception as e:
                        print(f"⚠️ Error parsing drug result: {e}")
                        continue
                if results:
                    cache_manager.set(cache_key, [result.dict() for result in results])
                    return results
            except Exception:
                continue

        print("❌ All search strategies exhausted (no matches)")
        return []
    
    def _parse_drug_result(self, item: Dict[str, Any]) -> Optional[OpenFDAResult]:
        """Parse a single drug result from OpenFDA API"""
        try:
            # Extract basic information
            application_number = item.get('application_number')
            
            # Extract openfda data
            openfda = item.get('openfda', {})
            
            # Extract products data
            products = item.get('products', [])
            first_product = products[0] if products else {}
            
            # Extract active ingredients
            active_ingredients = []
            if 'active_ingredients' in first_product:
                for ingredient in first_product['active_ingredients']:
                    active_ingredients.append({
                        'name': ingredient.get('name', ''),
                        'strength': ingredient.get('strength', '')
                    })
            
            # Build result
            result = OpenFDAResult(
                application_number=application_number,
                brand_name=openfda.get('brand_name', []),
                generic_name=openfda.get('generic_name', []),
                manufacturer_name=openfda.get('manufacturer_name', []),
                dosage_form=first_product.get('dosage_form'),
                route=first_product.get('route'),
                marketing_status=first_product.get('marketing_status'),
                active_ingredients=active_ingredients,
                pharm_class_epc=openfda.get('pharm_class_epc', []),
                pharm_class_moa=openfda.get('pharm_class_moa', []),
                pharm_class_pe=openfda.get('pharm_class_pe', []),
                sponsor_name=item.get('sponsor_name'),
                product_ndc=openfda.get('product_ndc', []),
                package_ndc=openfda.get('package_ndc', []),
                substance_name=openfda.get('substance_name', []),
                unii=openfda.get('unii', []),
                rxcui=openfda.get('rxcui', []),
                metadata={
                    'submissions': item.get('submissions', []),
                    'products': products,
                    'openfda': openfda
                }
            )
            
            return result
            
        except Exception as e:
            print(f"⚠️ Error parsing drug result: {e}")
            return None
    
    async def search_by_brand_name(self, brand_name: str, max_results: int = 50) -> List[OpenFDAResult]:
        """Search drugs by brand name"""
        search_query = f'openfda.brand_name:"{brand_name}"'
        return await self._search_openfda_drugs("", max_results, fielded_search=search_query)
    
    async def search_by_generic_name(self, generic_name: str, max_results: int = 50) -> List[OpenFDAResult]:
        """Search drugs by generic name"""
        search_query = f'openfda.generic_name:"{generic_name}"'
        return await self._search_openfda_drugs("", max_results, fielded_search=search_query)
    
    async def search_by_manufacturer(self, manufacturer: str, max_results: int = 50) -> List[OpenFDAResult]:
        """Search drugs by manufacturer"""
        search_query = f'openfda.manufacturer_name:"{manufacturer}"'
        return await self._search_openfda_drugs("", max_results, fielded_search=search_query)
    
    async def search_by_dosage_form(self, dosage_form: str, max_results: int = 50) -> List[OpenFDAResult]:
        """Search drugs by dosage form"""
        search_query = f'products.dosage_form:"{dosage_form}"'
        return await self._search_openfda_drugs("", max_results, fielded_search=search_query)
    
    async def search_by_route(self, route: str, max_results: int = 50) -> List[OpenFDAResult]:
        """Search drugs by route of administration"""
        search_query = f'products.route:"{route}"'
        return await self._search_openfda_drugs("", max_results, fielded_search=search_query)
    
    async def search_by_marketing_status(self, status: str, max_results: int = 50) -> List[OpenFDAResult]:
        """Search drugs by marketing status"""
        search_query = f'products.marketing_status:"{status}"'
        return await self._search_openfda_drugs("", max_results, fielded_search=search_query)
    
    async def search_by_pharmacologic_class(self, pharm_class: str, max_results: int = 50) -> List[OpenFDAResult]:
        """Search drugs by pharmacologic class"""
        search_query = f'openfda.pharm_class_epc:"{pharm_class}"'
        return await self._search_openfda_drugs("", max_results, fielded_search=search_query)
    

    
    async def search_recent_approvals(self, max_results: int = 50) -> List[OpenFDAResult]:
        """Search for recently approved drugs"""
        # Sort by submission date to get recent approvals
        search_query = "products.marketing_status:Prescription"
        return await self._search_openfda_drugs("", max_results, fielded_search=search_query)
    
    async def get_drug_details(self, application_number: str) -> Optional[OpenFDAResult]:
        """Get detailed information for a specific drug by application number"""
        search_query = f'application_number:"{application_number}"'
        results = await self._search_openfda_drugs("", 1, fielded_search=search_query)
        return results[0] if results else None
    
    async def count_drugs_by_field(self, field: str, search_query: str = "") -> Dict[str, Any]:
        """Count drugs by a specific field"""
        try:
            params = {
                'count': field,
                'limit': 1000  # Get more results for counting
            }
            
            if search_query:
                params['search'] = search_query
            
            response = await self._make_request(OPENFDA_ENDPOINTS["drugs"], params)
            
            return {
                'field': field,
                'search_query': search_query,
                'results': response.get('results', [])
            }
            
        except Exception as e:
            print(f"❌ OpenFDA count error: {e}")
            log_error(e, "OpenFDA count")
            return {}
    
    def _get_mock_results(self, query: str, max_results: int) -> List[OpenFDAResult]:
        """Get mock results for testing"""
        return [
            OpenFDAResult(
                application_number="NDA123456",
                brand_name=["MockDrug"],
                generic_name=["mock_drug"],
                manufacturer_name=["Mock Pharmaceuticals"],
                dosage_form="tablet",
                route="oral",
                marketing_status="Prescription",
                active_ingredients=[{"name": "mock_ingredient", "strength": "10mg"}],
                pharm_class_epc=["Mock Drug [EPC]"],
                pharm_class_moa=["Mock Mechanism [MoA]"],
                pharm_class_pe=["Mock Effect [PE]"],
                sponsor_name="Mock Pharmaceuticals",
                product_ndc=["12345-6789"],
                package_ndc=["12345-6789-01"],
                substance_name=["mock_substance"],
                unii=["MOCK123456"],
                rxcui=["123456"],
                relevance_score=0.8
            )
        ] 