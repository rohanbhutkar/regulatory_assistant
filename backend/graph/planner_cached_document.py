"""
Static graph-planner instructions (source list, rules, JSON shape) for Anthropic prompt caching.
Variable per-request fields (query, conversation, research brief) stay in the user message.
"""
from __future__ import annotations

from config import settings


def build_graph_planner_cached_document(max_nodes: int | None = None) -> str:
    """Large stable document; __MAX_NODES__ replaced (default: settings.GRAPH_PLAN_MAX_NODES)."""
    n = int(max_nodes if max_nodes is not None else settings.GRAPH_PLAN_MAX_NODES)
    return _CACHED_PLANNER_BODY.replace("__MAX_NODES__", str(n))


_CACHED_PLANNER_BODY = """
DOCUMENT — GRAPH PLANNING RULES (follow exactly for output shape and source selection)

TASK (for each request): Produce a JSON graph plan that efficiently answers the USER QUERY provided separately.

AVAILABLE SOURCES:
- "aact": Comprehensive clinical trials database with JOIN capabilities built on ClinicalTrials.gov
- "clinical_trials": ClinicalTrials.gov API (faster but limited)
- "trialtrove": Clinical trials database with detailed protocol and study design information (e.g. biomarker data, inclusion and exclusion criteria, endpoints, patient segments, and enrollment timelines) that are not available in the AACT database
- "pubmed": Medical publications database
- "biomcp": Biomedical ontology data
- "openfda": FDA drug information database (drug approvals, labels, safety data)
- "ema_eu": EMA / EU medicines **unified** search — see detailed capability list below (bulk JSON + ePI FHIR + optional PMS read). Use for EU centralised authorisations, EPARs, EMA publications, shortages, referrals, DHPC, PSUSA, PIP, orphan designations, ePI-style product information when identifiers/titles match.
- "china_regulatory": **China national** regulatory web discovery (CDE 药审中心, NMPA 国家药监局, zwfw 政务服务门户) via Google CSE scoped to official `.gov.cn` hosts + page text extraction. The agent **runs multiple parallel CSE query variations** (e.g. core terms + 药审中心 / 国家药监局 / 指导原则 angles), merges and ranks URLs, then fetches excerpts—similar in spirit to **ema_eu** multi-collection coverage. One focused node is often enough unless the query mixes unrelated China topics. Use for PRC guidance (指导原则), CDE/NMPA announcements, trial/regulatory rules on those sites—not for EU (use ema_eu) or general global web (use google_search). Put **Chinese keywords** in search_focus when QUERY is English but the topic is China-specific.
- "nih_reporter": NIH RePORTER **live API** — federal grant projects (titles, orgs, PIs, abstracts). Use for funding, NIH awards, institute activity—not for EU drug labels (use ema_eu).
- "npi_registry": CMS **NPI Registry** live API — US providers and organizations (NPI, practice location, taxonomy). Use for verifying sites/clinicians by name or 10-digit NPI.
- "openalex": OpenAlex live API — open bibliographic graph (works, citations, institutions). Use for publication landscape and open metadata beyond PubMed alone.
- "crossref": Crossref REST API — DOI metadata and publisher records (polite pool). Use for DOI resolution, publication registration, and journal/prefix discovery.
- "ror": ROR API — research organization IDs and relationships. Use to disambiguate sponsors, hospitals, and academic affiliations.
- "open_payments": CMS Open Payments **live API** — dataset catalog search and optional datastore rows if OPEN_PAYMENTS_DATASTORE_RESOURCE_IDS is configured. Use for sunshine / transfers-of-value style questions.
- "eu_ctis": EU CTIS **public** search API — **EU clinical trial applications** (registration-style). Use for EU trial lists; for EMA medicines, EPAR, shortages use **ema_eu** (do not duplicate both for the same EU drug-only question).
- "isrctn": ISRCTN **live API** — WHO-style trial registry query. Use for international trials registered on ISRCTN.
- "cms_open_data": CMS **data.cms.gov** Data API — hospital / FQHC enrollment-style facility rows (live). Use for US facility characteristics tied to CMS datasets (not a full custom site graph).
- "fda_datadashboard": FDA **Data Dashboard** API (inspections / import refusals) — **requires** FDA_DATADASHBOARD_USER and FDA_DATADASHBOARD_KEY. Use for FDA compliance/inspection/refusal questions when credentials are configured.
- "goodrx": GoodRx **web** drug pages (retail pricing context, coupons) via the GoodRx agent — may fall back to mock rows if blocked. Use for patient-facing US price orientation; use **payer_data** for formulary/rebate analytics.
- "fda_labels": FDA Structured Labels database with detailed drug label information including indications, contraindications, dosage, adverse reactions, clinical pharmacology, warnings, and drug interactions
- "google_search": General web search with custom instructions (news, research, industry updates). For search_focus and search_instructions, use the **language of the jurisdiction, regulator, or primary sources** (e.g. Chinese keywords for Chinese/NMPA regulations, Japanese for PMDA) when the topic is region-specific—even if the user wrote QUERY in English. The final answer to the user is still produced in English by the synthesize step.
- "claims_data": Healthcare claims, prescription, and patient data with advanced analysis capabilities:
  * ICD-10 diagnosis code analysis with flexible search terms and comprehensive statistics
  * CPT procedure code analysis with cost statistics and utilization data
  * HCPCS code analysis for medical supplies, equipment, and services
  * Comprehensive claims analysis with demographic insights and flexible filtering
  * Cost patterns analysis by diagnosis or procedure with detailed financial metrics
  * Patient demographics, prescription data, medical claims, and provider information
- "payer_data": Pharmaceutical sales, payer, and market data with sophisticated analysis capabilities:
  * Sales trends analysis with flexible search terms and comprehensive financial metrics
  * Market penetration analysis by payer plans and therapeutic areas
  * Payer rebates analysis with formulary coverage and financial insights
  * Formulary coverage analysis with tier placement and access metrics
  * Competitive landscape analysis by therapeutic area with market competition metrics
  * Customer segments analysis with purchasing patterns and behavior insights
  * Product information, sales data, payer plans, formulary tiers, and therapeutic areas
- "site_trove": Clinical trial site locations and trial-site relationships with comprehensive analysis capabilities:
  * Site search by name, location, type, or disease area with detailed site information
  * Geographic distribution analysis of trial sites by country, state, and region
  * Site capacity analysis including ongoing, planned, and available trial capacity
  * Trial-site relationship mapping showing which sites participate in specific trials
  * Site performance metrics including trial counts, disease areas, and contact information
- "site_map": Interactive site mapping with population overlays for clinical trial site selection:
  * Generate interactive maps showing recommended clinical trial sites
  * Population distribution overlays down to ZIP code level
  * Site recommendations based on trial experience and patient demographics
  * Geographic analysis with site scoring and filtering capabilities
  * Integration with trial data and claims data for comprehensive site selection
- "healthcare_analytics": Combined analytics from enhanced claims and payer data sources:
  * Drug utilization analysis combining prescription patterns with market data
  * Cost trends analysis across claims and payer perspectives
  * Patient population analysis with demographic and therapeutic insights
  * Market opportunity analysis leveraging both clinical and commercial data
  * Cross-source validation and correlation analysis
  * Comprehensive healthcare market intelligence

EMA_EU — WHAT CAN BE SEARCHED (single source id: ema_eu; one search node covers all of this):
- **Unified backend**: one `ema_eu` node runs EMA bulk JSON search, optional ePI FHIR calls, and optional PMS read — do **not** split into multiple nodes per feed.
- **EMA bulk JSON** (official twice-daily reports; full-text style match over cached JSON rows):
  * **medicines**: EU medicines catalogue / product records
  * **epar_documents**: EPAR-linked documents (assessment reports, SmPC-related publication workflow, refusals/withdrawals as published)
  * **post_authorisation**: post-authorisation changes (variations, extensions, label updates)
  * **non_epar_documents** / **all_documents**: other EMA document indices where applicable
  * **guidance**: EMA guidelines, scientific advice, procedural / ICH-related publications in the general JSON feed
  * **orphan_designations**: orphan / rare disease designations
  * **shortages**: medicine shortage / supply disruption notices
  * **referrals**: referral procedures (incl. PRAC-related referrals as published)
  * **dhpc**: Direct healthcare professional communications (DHPC / “dear doctor” style)
  * **psusa**: PSUR single assessments (PSUSA)
  * **pip**: Paediatric investigation plans (PIP)
- **How to plan the query string**: put **brand name, INN, ATC code, EMA procedure or product numbers, and document-type keywords** (e.g. “EPAR”, “variation”, “shortage”, “DHPC”, “PSUSA”, “PIP”, “orphan”, “referral”, “guidance”) in QUERY and in **search_focus** so the agent’s internal router can rank the right sub-collections.
- **ePI (FHIR, EMA.EPI.Consuming)** when enabled in server config: `GET …/consuming/api/fhir/List?title=…` then Bundle-by-id for narrative product information (SmPC-like HTML text). **List search is title-driven** — user wording may need to align with EMA list titles; no match means no ePI rows (not a failure of the planner). If the user states **PMS id** or **GTIN / data carrier identifier**, include them verbatim in the query — the agent can use Bundle search by `pms` / `carrierValue`.
- **PMS FHIR read** (`MedicinalProductDefinition` / `$everything`): only if the deployment sets `EMA_PMS_READ_ENABLED` and PMS base URL / auth — treat as **optional**, not default.
- **When to combine sources**: use **ema_eu** for EMA-held EU regulatory content; add **google_search** for **national** EU competent authorities, industry news, or topics EMA JSON/ePI are unlikely to cover.
- **Limitations to reflect in descriptions**: public feeds may be rate-limited; results are informational, not legal advice.

DYNAMIC CHAT SCOPE (no protocol drafting): Do **not** use `protocol_generate`, `protocol_full`, or any dedicated protocol-authoring node. If the user asks to draft or author a full protocol or sections, answer with **search + synthesize** only (e.g. summarize evidence and outline considerations in prose—do not plan generation nodes).

SITE TROVE REQUIREMENTS:
- When using site_trove for site analysis, ALWAYS use trialtrove as a source to get trial details
- site_trove provides site locations, counts and experience but trialtrove provides detailed trial information

SIMULATION DETECTION:
-- Include simulation node when query mentions: "simulate", "simulation", "predict", "forecast", "timeline", "enrollment", "recruitment", "budget", "cost", "risk assessment", "feasibility", "success probability"
-- Include simulation node for queries about: trial planning, enrollment forecasting, budget projections, risk analysis, timeline predictions, feasibility studies
-- Simulation provides: recruitment curves, milestone tracking, budget projections, risk assessment, success probability analysis
-- Use simulation node for comprehensive trial planning and analysis queries

SITE MAP DETECTION:
-- Include site_map node when query mentions: "site map", "site mapping", "population distribution", "geographic analysis", "site recommendations", "patient distribution", "clinical trial locations", "where are patients", "best sites", "site selection", "population overlay", "sites used", "sites in", "sites for", "trial sites", "clinical sites", "study sites", "site locations", "site information", "site details", "site analysis", "site data"
-- Include site_map node for queries about: interactive maps, site visualization, population density, geographic site analysis, patient location analysis, site scoring, site filtering, site identification, site discovery, site research, site investigation
-- Site map provides: interactive maps with site pins, population overlays, site scoring, geographic analysis, patient distribution visualization, site identification and analysis
-- Use site_map node for comprehensive site selection and geographic analysis queries, site identification queries, and any query asking about sites in clinical trials
-- IMPORTANT: Use node type "site_map" (not "search" with source "site_map") for site mapping functionality
-- CRITICAL: Site map uses TrialTrove for trial data and SiteTrove for site locations - NEVER use AACT for site-related queries

ENHANCED ANALYSIS CAPABILITIES:

CLAIMS DATA ANALYSIS:
- Use claims_data for queries about: ICD codes, CPT codes, HCPCS codes, diagnosis analysis, procedure analysis, cost patterns, demographic analysis
- Enhanced capabilities include:
  * ICD-10 code analysis with flexible search terms and comprehensive statistics
  * CPT procedure code analysis with cost statistics and utilization data
  * HCPCS code analysis for medical supplies, equipment, and services
  * Comprehensive claims analysis with demographic insights and flexible filtering
  * Cost patterns analysis by diagnosis or procedure with detailed financial metrics
- Keywords that trigger enhanced analysis: "ICD codes", "CPT codes", "HCPCS codes", "comprehensive analysis", "cost patterns", "demographic analysis"

PAYER DATA ANALYSIS:
- Use payer_data for queries about: sales trends, market penetration, payer rebates, formulary coverage, competitive landscape, customer segments
- Enhanced capabilities include:
  * Sales trends analysis with flexible search terms and comprehensive financial metrics
  * Market penetration analysis by payer plans and therapeutic areas
  * Payer rebates analysis with formulary coverage and financial insights
  * Formulary coverage analysis with tier placement and access metrics
  * Competitive landscape analysis by therapeutic area with market competition metrics
  * Customer segments analysis with purchasing patterns and behavior insights
- Keywords that trigger enhanced analysis: "sales trends", "market penetration", "payer rebates", "formulary coverage", "competitive landscape", "customer segments"

NODE TYPES:
- "search": Query a specific data source (requires "source" parameter)
- "analyze": Process and analyze results from previous nodes (requires "analysis_type" parameter)
- "synthesize": Combine insights into final answer (requires "synthesis_type" parameter)
- "filter": Filter results based on criteria (requires "filter_criteria" parameter)
- "extract": Extract specific information (requires "extraction_fields" parameter)
- "simulation": Run clinical trial simulation with MCMC modeling (no additional parameters required)

GENERAL PRINCIPLES:
1. Use the most appropriate data source for the query type
2. For complex queries, consider multiple google_search nodes with different topics/focus areas
3. You may use up to __MAX_NODES__ nodes total (including synthesize and any simulation nodes). When the USER message begins with a STRICT BUDGET block, obey that block exactly (it overrides this generic cap). Otherwise, for broad queries merge redundant searches when one node suffices; simple queries should use fewer nodes.
4. Use analysis nodes to process and interpret results
7. Ensure logical execution order
8. Consider conversation history context when planning - if previous questions were asked, build upon that context
9. If the query references previous information, ensure the plan can access and build upon that context
10. Use AACT OR CLINICAL TRIALS, do not use multiple ClinicalTrials.gov sources
11. CRITICAL: For site-related queries (site locations, site mapping, site analysis), use TrialTrove and SiteTrove - NEVER use AACT
12. ALWAYS include a "synthesize" node to produce a conversational chat answer.
13. USER-FACING LANGUAGE: The synthesize node's final answer must be **English** (for the product UI). Web search nodes may still use non-English search_focus/search_instructions when needed to retrieve the best regional or regulatory sources.
14. **EU / EMA regulatory questions** (centralised authorisations, EPARs, EMA guidance, shortages, referrals, DHPC, PSUSA, PIP, orphan status, ePI / SmPC-style product information on EMA): include at least one **ema_eu** search node with a **search_focus** that names the product and the document type or topic. Use **google_search** additionally for non-EMA EU national agencies or when the user explicitly wants broader web sources.
15. **China / CDE / NMPA regulatory questions** (PRC national rules, CDE technical guidelines, NMPA drug registration notices, zwfw service pages on official hosts): include at least one **china_regulatory** search node with **search_focus** in Chinese when appropriate. Use **google_search** for non-official commentary, industry news, or English-only secondary sources; use **ema_eu** only for EU—not for China.
16. **Regulatory comparison across jurisdictions** (e.g. “FDA vs NMPA”, “US vs China preclinical”, “EMA compared to FDA engagement”): include **at least one search node per jurisdiction** in the query—e.g. **google_search** with `search_focus` on FDA/ICH/federal register/guidance pages for the US side, plus **china_regulatory** (Chinese `search_focus`) for NMPA/CDE. Do **not** satisfy a two-sided compare with a single generic web search. Follow with an **analyze** node with top-level **`analysis_type`: `compare`** and string **`analysis_focus`** naming the exact dimensions (e.g. “pre-IND/IND communication, GLP, meeting types, timing, required vs optional agency touchpoints”). Node descriptions should ask for **document titles, numbers, dates, and quotable procedural language** from retrieved text—not high-level summaries.
17. **max_results for regulatory / web excerpt sources**: For **google_search**, **china_regulatory**, and **ema_eu** nodes when the query is regulatory or comparative, set **`max_results` to at least 24–30** (up to API limits) so synthesis receives enough long excerpts—avoid single-digit or minimal counts.

MULTIPLE GOOGLE SEARCH GUIDELINES:
- Use multiple google_search nodes when the query covers multiple aspects (clinical, market, regulatory, patient, competitive)
- Each google_search node should have a unique search_focus that targets a specific aspect
- Distribute max_results across nodes (e.g., 15 results per node instead of 30 in one node)
- Use descriptive node IDs like "search_google_clinical", "search_google_market", "search_google_regulatory"

GOOGLE SEARCH STRATEGY:
- For complex queries, create multiple google_search nodes with different search_focus and search_instructions
- Each google_search node should target a specific aspect or topic
- SEARCH LANGUAGE (not the same as answer language): Use the **language that matches the topic's primary sources**—e.g. Chinese terms for PRC/NMPA/国家药监局 rules, German for German BfArM pages—especially when QUERY is in English but asks about a non-English jurisdiction. Prefer local/regional domains and official agencies. Use English search terms when the topic is US/UK/global-English sources or the user explicitly wants English-only results.
- Examples of multiple search strategies:
  * Node 1: "clinical trials" + "focus on recent Phase 3 results and breakthrough therapies"
  * Node 2: "market analysis" + "include industry reports, financial data, and market forecasts"
  * Node 3: "regulatory updates" + "FDA approvals, safety alerts, and regulatory decisions"
  * China regulatory example (QUERY may be English): prefer **china_regulatory** with **search_focus** in Chinese (product/INN Chinese name, disease, trial phase) and **search_instructions** with **granular filters**: document type (指导原则, 通告, 公示, 征求意见稿), year or batch number if known, and whether CDE vs NMPA vs zwfw matters—the agent attaches instructions across parallel CSE angles when space allows. Use **google_search** only for broader web or English secondary sources.
  * Node 4: "patient outcomes" + "real-world evidence, patient experiences, and quality of life data"
  * Node 5: "competitive landscape" + "competitor analysis, partnerships, and market positioning"

PLAN SIZE: Do not exceed __MAX_NODES__ entries in the "nodes" array (each search/analyze/synthesize/etc. counts as one).

Return ONLY valid JSON without markdown formatting:

{
    "reasoning": "Brief explanation of the approach",
    "nodes": [
        {
            "id": "search_node_id",
            "type": "search",
            "description": "What this search node does",
            "parameters": {
                "source": "aact|clinical_trials|pubmed|biomcp|openfda|ema_eu|china_regulatory|fda_labels|google_search|trialtrove|claims_data|payer_data|healthcare_analytics|goodrx|nih_reporter|npi_registry|openalex|crossref|ror|open_payments|eu_ctis|isrctn|cms_open_data|fda_datadashboard",
                "max_results": 28,
                "search_focus": "search strategy",
                "outline_section_id": "section_id_from_brief_when_applicable_or_empty_string",
                "facet": "regulatory|clinical|commercial|sites|publications|meta",
                "search_instructions": "hints for google_search and china_regulatory: region, official agencies, recency (English OK; use topic-appropriate language in search_focus for non-English jurisdictions). For regulatory/compare topics prefer 24–30 max_results."
            },
            "dependencies": []
        },
        {
            "id": "analyze_node_id",
            "type": "analyze",
            "description": "What this analysis node does",
            "parameters": {
                "analysis_type": "categorize|compare|identify_trends|assess_quality|extract_patterns",
                "analysis_focus": "specific aspects to analyze"
            },
            "dependencies": ["search_node_id"]
        },
        {
            "id": "synthesize_node_id",
            "type": "synthesize",
            "description": "What this synthesis node does",
            "parameters": {
                "synthesis_type": "comprehensive_summary|structured_report|evidence_assessment|clinical_recommendations"
            },
            "dependencies": ["analyze_node_id"]
        }
    ],
    "edges": [
        {"from": "search_node_id", "to": "analyze_node_id"},
        {"from": "analyze_node_id", "to": "synthesize_node_id"}
    ],
    "execution_order": ["search_node_id", "analyze_node_id", "synthesize_node_id"]
}

When INTERNAL RESEARCH BRIEF is present in the user message:
- Each search node MUST include in parameters: "outline_section_id" (string matching a section_id) and "facet" (one of: regulatory, clinical, commercial, sites, publications, meta).
- Add explicit "dependencies" between nodes when later searches should refine queries using earlier results (enables dynamic follow-up search strings).
"""
