# Study Designer — agents log

Last updated: 2026-04-07

This document lists **agent modules and reasoning-graph agents** in `study_designer`, then maps **site database** data pipelines to **additional agents** you could add later.

---

## 1. Python modules under `backend/agents/`

| File | Role |
|------|------|
| `aact_agent.py` | AACT / trial detail queries |
| `biomcp_agent.py` | BioOntology / MCP concepts |
| `china_regulatory_agent.py` | CDE / NMPA / China regulatory web discovery |
| `claims_data_agent.py` | Claims analysis (lazy-loaded in engine) |
| `clinical_trials_agent.py` | ClinicalTrials.gov |
| `ema_eu_agent.py` | EMA / EU medicines JSON + ePI paths |
| `ema_epi_client.py` | EMA ePI client helper |
| `ema_json_index.py` | EMA JSON index helper |
| `ema_pms_client.py` | EMA post-marketing helper |
| `ema_query_router.py` | EMA query routing helper |
| `fda_labels_agent.py` | FDA structured labels |
| `fierce_pharma_agent.py` | Web search (exports `google_search_agent`) |
| `goodrx_agent.py` | Drug pricing |
| `healthcare_analytics_agent.py` | Combined claims + payer analytics (lazy) |
| `hitl_agent.py` | Human-in-the-loop trial selection (wired but HITL disabled) |
| `insights_agent.py` | Portfolio / insights (API via `get_insights_agent`, not in reasoning graph) |
| `llm_agent.py` | General LLM synthesis |
| `openfda_agent.py` | OpenFDA drug / device / enforcement APIs |
| `payer_data_agent.py` | Payer / market data (lazy) |
| `protocol_authoring_agent.py` | Protocol generation |
| `protocol_authoring_agent_original.py` | Earlier protocol author (legacy duplicate) |
| `enhanced_protocol_authoring_agent.py` | Alternate protocol author (no current imports in `backend/`) |
| `pubmed_agent.py` | PubMed literature |
| `simulation_agent.py` | Trial startup / enrollment simulation |
| `site_map_agent.py` | Geographic site mapping |
| `site_trove_agent.py` | Site selection / performance |
| `soa_extractor_agent.py` | Schedule of activities extraction |
| `trialtrove_agent.py` | TrialTrove proprietary trial data |
| `asset_strategy_agent.py` | Asset strategy chat / tools (used by `api/asset_ai_routes.py`, not in reasoning graph) |
| `nih_reporter_agent.py` | NIH RePORTER live API |
| `npi_registry_agent.py` | CMS NPI Registry live API |
| `openalex_agent.py` | OpenAlex live API |
| `crossref_agent.py` | Crossref REST API |
| `ror_agent.py` | ROR organizations API |
| `open_payments_agent.py` | CMS Open Payments live API |
| `eu_ctis_agent.py` | EU CTIS public search API |
| `isrctn_agent.py` | ISRCTN query API |
| `cms_open_data_agent.py` | CMS data.cms.gov Data API |
| `fda_datadashboard_agent.py` | FDA Data Dashboard API (auth) |
| `llm_agent.py` | Already listed |

---

## 2. `DynamicReasoningEngine` graph agents (`backend/graph/dynamic_reasoning_engine.py`)

These keys are what the multi-agent planner and `/api/agents` / health endpoints expose.

| Graph key | Implementation | Notes |
|-----------|----------------|--------|
| `clinical_trials` | `clinical_trials_agent` | |
| `pubmed` | `pubmed_agent` | |
| `biomcp` | `biomcp_agent` | |
| `aact` | `aact_agent` | |
| `aact_soa` | `aact_agent` | Same instance; SoA path |
| `openfda` | `OpenFDAAgent()` | |
| `google_search` | `google_search_agent` (from `fierce_pharma_agent`) | |
| `trialtrove` | `trialtrove_agent` | |
| `fda_labels` | `fda_labels_agent` | |
| `protocol_authoring` | `protocol_authoring_agent` | |
| `simulation` | `simulation_agent` | |
| `site_trove` | `site_trove_agent` | |
| `site_map` | `site_map_agent` | |
| `llm` | `llm_agent` | |
| `goodrx` | `goodrx_agent` | |
| `soa_extractor` | `soa_extractor_agent` | |
| `ema_eu` | `ema_eu_agent` | |
| `china_regulatory` | `china_regulatory_agent` | |
| `claims_data` | `claims_data_agent` | Initialized on first use (`None` at startup) |
| `payer_data` | `payer_data_agent` | Initialized on first use |
| `healthcare_analytics` | `healthcare_analytics_agent` | Initialized on first use |
| `hitl_trial_selection` | `hitl_agent` | Lazy init; HITL path disabled |
| `nih_reporter` | `nih_reporter_agent` | Live NIH grants/projects API |
| `npi_registry` | `npi_registry_agent` | Live NPI Registry |
| `openalex` | `openalex_agent` | Live OpenAlex |
| `crossref` | `crossref_agent` | Live Crossref |
| `ror` | `ror_agent` | Live ROR |
| `open_payments` | `open_payments_agent` | Live Open Payments |
| `eu_ctis` | `eu_ctis_agent` | Live EU CTIS search |
| `isrctn` | `isrctn_agent` | Live ISRCTN |
| `cms_open_data` | `cms_open_data_agent` | Live CMS Data API |
| `fda_datadashboard` | `fda_datadashboard_agent` | Live FDA DDAPI (needs keys) |

**Not in the reasoning graph (separate API surfaces):**

- `asset_strategy_agent` → `/api/asset-strategy/...` AI routes  
- `insights_agent` → `/api/insights` via `get_insights_agent(data_loader)`

---

## 3. Site database (`…/site database`) — extra agents you could build

The site database project is a **Postgres + ETL graph** for trials, sites, people, orgs, and capabilities. Its `backend/etl/` pipelines ingest many sources that **do not** have a dedicated study_designer reasoning agent today. Strong candidates:

| Source / pipeline | Module (indicative) | Possible agent focus |
|-------------------|---------------------|----------------------|
| NIH Reporter | `nih_reporter_ingest.py` | Grant-funded sites, PI funding, trial–grant linkage |
| OpenAlex | `openalex_ingest.py` | Publications, institutions, open citations |
| Crossref | `crossref_ingest.py` | DOI metadata, publisher links |
| ROR | `ror_ingest.py` | Research organization IDs, parent/child orgs |
| NPPES | `nppes_ingest.py` | NPI lookup, provider/org enrichment (API ref in `backend/reference/`) |
| FDA BMIS (Form 1572) | `fda_bmis_ingest.py` | PI/site legal names, attestation vs registry |
| FDA inspections | `fda_inspection_ingest.py` | Site inspection history |
| FDA mammography MQSA | `fda_mammography_ingest.py` | Facility certification context |
| OHRP | `ohrp_ingest.py` | IRB / human subjects registration signals |
| CMS CLIA | `cms_clia_ingest.py` | Lab certification |
| CMS hospital / HPT / POS | `cms_hospital_ingest.py`, `cms_hpt_ingest.py`, `cms_pos_ingest.py` | Facility type, place of service, hospital compare |
| CMS MRF | `mrf_ingest.py` | Machine-readable pricing (where modeled) |
| Open Payments | `open_payments_ingest.py` | Sunshine / transfers of value |
| CTIS | `ctis_ingest.py` | EU CTIS registry (complements EMA JSON agent) |
| ISRCTN | `isrctn_ingest.py` | WHO ICTRP-style trial IDs |
| SRTR | `srtr_ingest.py` | Transplant program outcomes |
| AABB | `aabb_ingest.py` | Blood / cellular therapy accreditation |
| CAP directory | `cap_directory_ingest.py` | Lab accreditation directory |
| NCI | `capability_nci_ingest.py` | Cancer center / NCI-linked capability signals |
| Google fallback (ETL) | `google_search_fallback.py` | Operational fallback, not end-user search |
| Site URL from ROR | `site_url_from_ror.py` | Website discovery for sites |

**Already overlapping** with existing study_designer agents (less need for a *new* agent unless you want DB-backed depth): `aact_ingest`, `pubmed_ingest`, `trial_publication_from_aact`, and capability rollups (`capability_*.py`).

**Design note from site DB docs:** `CLEAN_SOURCES_GRAPH.md` describes treating **BMIS** (and similar) as authority for legal names → aliases → better NPI resolution. A **“site graph” or “NPI resolution” agent** that queries your unified schema (rather than only public APIs) would align with that architecture.

---

## 4. Quick gaps summary

1. **In repo but not on the multi-agent graph:** `asset_strategy_agent`, `insights_agent`; legacy `enhanced_protocol_authoring_agent` / `protocol_authoring_agent_original`.  
2. **Lazy agents:** `claims_data`, `payer_data`, `healthcare_analytics` start as `None` until first use.  
3. **Site database–only sources:** dozens of ETL-backed domains (NIH Reporter, OpenAlex, CMS family, BMIS, NPPES, etc.) are natural **new agent** targets if you expose that DB to study_designer or wrap the same APIs the ETL uses.

---

## 5. Live API graph agents (implemented)

These use **public HTTP APIs only** (no site database). Each exposes `search(query, max_results)` and returns `LiveDataSearchResult` (`models/schemas.py`). Registered in `DynamicReasoningEngine` as `LIVE_API_GRAPH_SOURCES` and listed on `GET /api/agents`.

| `source` | Module | Notes |
|----------|--------|--------|
| `nih_reporter` | `agents/nih_reporter_agent.py` | POST `api.reporter.nih.gov/v2/projects/search`; respect ≤1 rps. |
| `npi_registry` | `agents/npi_registry_agent.py` | CMS NPI Registry v2.1. |
| `openalex` | `agents/openalex_agent.py` | Optional `OPENALEX_API_KEY`. |
| `crossref` | `agents/crossref_agent.py` | Set `CROSSREF_MAILTO` for polite pool. |
| `ror` | `agents/ror_agent.py` | ROR v2 organizations query. |
| `open_payments` | `agents/open_payments_agent.py` | Metastore catalog + optional `OPEN_PAYMENTS_DATASTORE_RESOURCE_IDS`. |
| `eu_ctis` | `agents/eu_ctis_agent.py` | POST EU CTIS public search. |
| `isrctn` | `agents/isrctn_agent.py` | GET ISRCTN query API. |
| `cms_open_data` | `agents/cms_open_data_agent.py` | `data.cms.gov` Data API v1 (hospital + FQHC enrollment datasets). |
| `fda_datadashboard` | `agents/fda_datadashboard_agent.py` | Requires `FDA_DATADASHBOARD_USER` / `FDA_DATADASHBOARD_KEY`. |

Config and env template: `backend/config.py`, `backend/.env.example`. Shared helpers: `backend/utils/live_api_http.py`.

---

## 6. Deferred (not live REST / bulk-only)

Per rollout plan, these **do not** have a single stable public REST surface suitable for the same pattern; use **`google_search`**, official portals, or a future **bulk-file** pipeline—not the graph agents above.

- **BMIS (FDA 1572), OHRP, CAP directory, AABB, SRTR, MRF bulk** — downloads, portals, or specialized scrapers; not implemented as live agents here.
