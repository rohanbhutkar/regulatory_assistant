# Integrated Data Source Usage Table

Grouped working view of data needs for the feasibility and study design workflow, followed by the detailed source inventory found across the repo.

## Grouped Working View

| Data Source Type | Example Sources | Used For |
| --- | --- | --- |
| Trial data | ClinicalTrials.gov / CT.gov, AACT, TrialTrove, EU CTIS, ISRCTN, DQS or equivalent source-quality feed | Reference trial search; comparator trial benchmarking; protocol generation; objective/endpoint extraction; inclusion/exclusion criteria patterns; enrollment priors; site-count benchmarks; trial timing/status comparisons. |
| Site and investigator data | SiteTrove, Site Map Agent, NPI/NPPES, ROR, CMS Open Data, BMIS, OHRP, CLIA, CAP, AABB, SRTR, NCI site lists | Site identification; site-count benchmarks; site feasibility; investigator/site performance; geographic coverage; selected-site export; site capability and historical trial participation review. |
| Claims / RWD data | Claims Data (`data/claims/combined_claims.csv`), Claims Data Agent, Healthcare Analytics Agent, Payer Plans Claims Fact | Eligible population sizing; ICD-based prevalence; inclusion/exclusion impact; screen-failure assumptions; enrollment feasibility; demographics and geography; utilization context. |
| Cost and budget data | CPP Clinical Procedures, SPU Standard Pricing Units, CPP Drug Costs, ODCs, OPAL, Country Specifications, Golden Rules, Overhead Rules, Rule Matrix, Indications | Schedule of Activities procedure mapping; CPT/procedure normalization; per-patient and per-site costs; country/indication modifiers; operational workload; budget line items; overhead and contingency assumptions. |
| Payer and market access data | Payer Plan, Formulary Tier, Payer Plans Claims Fact, Product Brand/NDC, Therapeutic Area/Class, Market Basket, Sales Fact, Sales Forecast Fact | Coverage and formulary tiering; GTN/rebate/access modeling; comparator product identification; market basket definition; sales/forecast context; payer segmentation. |
| Regulatory and label data | FDA Structured Labels, OpenFDA, FDA Data Dashboard, EMA public JSON, EMA ePI, EMA PMS, CDE/NMPA | Label and indication context; safety/warning review; regulatory precedent; approval and inspection signals; regional requirements; regulatory rationale for protocol content. |
| Literature and evidence data | PubMed, PubMed Central OAI, OpenAlex, Crossref, NIH RePORTER | Disease background; treatment landscape; unmet need; evidence synthesis; publication/citation support; investigator and institution evidence signals. |
| Drug pricing and commercial data | GoodRx, CPP Drug Costs, SPU, Product Brand/NDC, Sales Fact, Sales Forecast Fact, Open Payments | Comparator pricing; retail/drug cost assumptions; commercial context; payment/transparency signals; asset and comparator strategy inputs. |
| Ontology, coding, and taxonomy data | NCBO BioPortal / BioOntology, MeSH, ICD fields from TrialTrove and claims, CPT/procedure catalog, therapeutic area/class dimensions | Disease/procedure/drug normalization; ICD/CPT mapping; search expansion; criteria-to-code matching; endpoint, indication, and procedure categorization. |
| Geography, demographics, and territory data | SiteTrove location fields, claims geography, Geography Dimension, Territory Dimension, ZIP to Territory, Address Dimension, pgeocode/ZIP geocoder, SDOH fields | Site maps; population heatmaps; country/state/region filtering; territory planning; geographic coverage; diversity/access feasibility filters. |
| Operational and field engagement data | Call Header, Call Details, Call Plan, Call Sample, Campaign, Channel, Goals by Territory, HCP/HCO, HCP Segment/Trait/Privacy, Affiliations | Field targeting; account/territory planning; HCP/HCO segmentation; engagement history; privacy-aware outreach; operational readiness context. |
| Web, guidance, and current-awareness data | Google Custom Search, Web/Guidance Agent, CDE/NMPA scoped search, Fierce/industry pages discovered through search | Current guidance/news discovery; horizon scanning; source finding for research, regulatory, commercial, and feasibility questions. |
| Uploaded documents and generated study artifacts | Regulatory chat uploads, protocol sections, Schedule of Activities extractor outputs, generated protocol/objective/endpoint/IE artifacts | Grounding generated content in uploaded files; extracting SoA tables; protocol generation; review traceability; export-ready study design artifacts. |
| Derived analytics and AI outputs | Simulation Agent, Site Map Agent outputs, Healthcare Analytics Agent outputs, AI Insights Agent outputs, LLM summaries | Enrollment curves; milestone and risk projections; success probability; feasibility recommendations; budget pressure; country/site coverage analytics. |
| Data catalog and provenance metadata | DataCatalogService, MPI Table List, source quality scores, refresh metadata, source registry configuration | Source registration; ownership/coverage tracking; refresh and quality monitoring; auditability; data-source selection and explainability. |
| Manual study design inputs | Basic Info tab, selected reference trials/sites, edited eligibility criteria, objectives/endpoints, SoA mappings, simulation overrides | Core assumptions for all downstream workflows; user-authored overrides; final protocol, feasibility, simulation, site, and budget outputs. |

## Detailed Source Inventory

Single-table inventory of data sources found across the repo. "Source type" includes whether the source is a local dataset, live API, composite agent, or documented future/site-database source.

| Data Source Type | Explicit Source Name | Used For |
| --- | --- | --- |
| Local clinical-trial dataset | TrialTrove (`data/combined_trial_trove.csv`) | Reference trial search, comparator trial benchmarking, protocol generation, objective/endpoint extraction, IE criteria patterns, enrollment priors, site-count benchmarks. |
| Local site-performance dataset | SiteTrove (`data/combined_site_trove.csv`) | Site selection, trial-site mapping, site performance metrics, investigator/site history, geographic map overlays, recommended site selection. |
| Local claims / RWD dataset | Claims Data (`data/claims/combined_claims.csv`) | ICD population analysis, eligibility funnel estimates, geography/demographic distribution, patient prevalence, claims-backed criterion impact. |
| Local regulatory label dataset | FDA Structured Labels (`data/FDA_Structured_Labels.xlsx`) | Drug label search, indication and warning context, mechanism/label evidence, regulatory comparison, comparator and asset strategy support. |
| CPP procedure reference | CPP Clinical Procedures (`data/cpp/clinical_procedures/Reference_Clinical_Procedures_2025_Q2.csv`) | SoA procedure mapping, CPT/procedure normalization, per-procedure cost lookup, budget line-item support. |
| CPP country pricing reference | SPU Standard Pricing Units (`data/cpp/spu/Reference_SPU_All_Countries_2025.csv`) | Country-level FMV/SPU pricing, international procedure pricing, country budget assumptions. |
| CPP drug-cost reference | CPP Drug Costs (`data/cpp/drugs/Reference_Drug_Costs_2024_Q1_Historical.csv`) | Comparator drug cost benchmarking, historical drug pricing, asset pricing assumptions. |
| CPP country rules | CPP Country Specifications (`data/cpp/rules/Reference_Country_Specifications.csv`) | Country-specific costing rules, market adjustments, overhead/cost multipliers, HTA/pricing assumptions. |
| CPP indication rules | CPP Indications (`data/cpp/rules/Reference_Indications_2025_Q1.csv`) | Indication and therapeutic-area rules, disease-specific cost/HTA logic, budget and market assumptions. |
| CPP indication-change rules | CPP Indication Additions/Retirements (`data/cpp/rules/Reference_Indications_AdditionsRet_2025_Q1.csv`) | Tracking indication updates, additions, retirements, and rule maintenance. |
| CPP overhead rules | CPP Overhead Rules (`data/cpp/rules/Reference_Overhead_Rules.csv`) | Budget overhead calculations and overhead-rate rule application. |
| CPP rule matrix | CPP Comprehensive Rule Matrix (`data/cpp/rules/Reference_Rule_Matrix_Comprehensive.csv`) | Applying combined budget/CPP rules across procedure, country, indication, and operational dimensions. |
| CPP global rules | CPP Golden Rules (`data/cpp/rules/Reference_Golden_Rules.csv`) | Global/default budget and CPP adjustment rules. |
| CPP operational workload | OPAL Complete (`data/cpp/opal/Reference_OPAL_Complete.csv`) | Operational workload estimates, staffing assumptions, project activity-level effort. |
| CPP operational formulas | OPAL Formulas Detail (`data/cpp/opal/Reference_OPAL_Formulas_Detail.csv`) | OPAL calculation explainability and formula detail. |
| CPP operational sheet | OPAL Sheet (`data/cpp/opal/Reference_OPAL_Sheet.csv`) | OPAL source table/reference values for operational budget calculations. |
| CPP other direct costs | ODCs (`data/cpp/odcs/Reference_ODCs_2025_Q2.csv`) | Other direct cost assumptions outside clinical procedures. |
| CPP additional activity costs | Additional Activities ODCs (`data/cpp/odcs/Reference_Additional_Activities_ODCs.csv`) | Additional activity-level cost assumptions for budget enrichment. |
| Payer dimension table | Address Dimension (`data/payer_data/Address_Dim.csv`) | Customer/HCP/HCO address enrichment and geography linking. |
| Payer promotional table | Ads (`data/payer_data/Ads.csv`) | Promotional/activity context and commercial campaign analytics. |
| Payer affiliation table | Affiliations Dimension (`data/payer_data/Affiliations_Dim.csv`) | HCP/HCO affiliation mapping, network relationships, account structure. |
| Payer sales fact table | BioSymphony Sales Fact (`data/payer_data/BioSymphonySalesFact.csv`) | Prescription/sales analytics, prescriber-payer views, market performance signals. |
| Payer segmentation table | Business Segment Dimension (`data/payer_data/Business_Segment_Dim.csv`) | Business segment classification and reporting cuts. |
| Payer call fact table | Call Header Fact (`data/payer_data/Call_Header_Fact.csv`) | Field engagement/call activity analytics. |
| Payer call detail table | Call Key Details Dimension (`data/payer_data/Call_Key_Details_Dim.csv`) | Call metadata and detailed activity classification. |
| Payer planning table | Call Plan Dimension (`data/payer_data/Call_Plan_Dim.csv`) | Call planning, field force targeting, planned engagement analysis. |
| Payer sample table | Call Sample Dimension (`data/payer_data/Call_Sample_Dim.csv`) | Sample activity and call sample tracking. |
| Payer campaign table | Campaign Dimension (`data/payer_data/Campaign_Dim.csv`) | Campaign attribution and commercial activity grouping. |
| Payer channel table | Channel Dimension (`data/payer_data/Channel_Dim.csv`) | Channel classification for calls, campaigns, and sales activity. |
| Payer customer table | Customer Dimension (`data/payer_data/Customer_Dim.csv`) | Customer master data, HCP/HCO/customer analytics, market access context. |
| Payer specialty relationship table | Customer Specialty Relationship (`data/payer_data/Customer_Speciality_Relationship_Dim.csv`) | Customer specialty mapping and segmentation. |
| Payer calendar table | Date Dimension (`data/payer_data/Date_Dim.csv`) | Time-series joins, monthly/quarterly reporting, forecast alignment. |
| Payer delta table | Delta Customer Dimension (`data/payer_data/Delta_Customer_Dim.csv`) | Customer change tracking and incremental updates. |
| Payer formulary table | Formulary Tier Dimension (`data/payer_data/Formulary_Tier_Dim.csv`) | Formulary tiering, coverage/access modeling, GTN calculations. |
| Payer duplicate/reference copy | Formulary Tier Dimension Copy (`data/payer_data/Formulary_Tier_Dim copy.csv`) | Duplicate/backup formulary tier data; useful for reconciliation or cleanup. |
| Payer geography table | Geography Dimension (`data/payer_data/Geography_Dim.csv`) | Market geography, territory mapping, geographic analytics. |
| Payer goals table | Goals by Territory Dimension (`data/payer_data/Goals_by_Territory_Dim.csv`) | Territory goals, performance targets, field planning. |
| Payer organization table | HCO Dimension (`data/payer_data/HCO_Dim.csv`) | Healthcare organization master data and account analytics. |
| Payer provider table | HCP Dimension (`data/payer_data/HCP_Dim.csv`) | HCP master data, prescriber analysis, targeting and segmentation. |
| Payer privacy table | HCP Privacy Preferences Dimension (`data/payer_data/HCP_Privacy_Prefrences_Dim.csv`) | Communication/privacy constraints and compliant engagement filtering. |
| Payer segment table | HCP Segment Dimension (`data/payer_data/HCP_Segment_Dim.csv`) | HCP segmentation, targeting, persona/decile grouping. |
| Payer trait table | HCP Trait Dimension (`data/payer_data/HCP_Trait_Dim.csv`) | HCP attributes and behavioral/segment enrichment. |
| Payer identifier table | Identifiers Dimension (`data/payer_data/Identifiers_Dim.csv`) | Cross-system ID mapping and entity resolution. |
| Payer metadata workbook | MPI Table List (`data/payer_data/MPI_Table_List.xlsx`) | Payer data table catalog/metadata and source inventory. |
| Payer market basket table | Market Basket Dimension (`data/payer_data/Market_Basket_Dim.csv`) | Market basket definition, competitor grouping, market access analysis. |
| Payer market table | Market Dimension (`data/payer_data/Market_Dim.csv`) | Market classification and reporting groups. |
| Payer territory-ZIP table | Market Territory ZIP Relationship (`data/payer_data/Marketterrziprelationship_Dim.csv`) | ZIP-to-market/territory mapping and geographic rollups. |
| Payer plan table | Payer Plan Dimension (`data/payer_data/Payer_Plan_Dim.csv`) | Payer/plan metadata, coverage analysis, payer segmentation. |
| Payer claims fact table | Payer Plans Claims Fact (`data/payer_data/Payer_Plans_Claims_Fact.csv`) | Payer claims, rebates/access distributions, GTN and market access modeling. |
| Payer relationship table | Product Brand to Business Segment Relationship (`data/payer_data/Product_Brand_Business_Segment_Relationship_Dim.csv`) | Product-to-business-segment mapping. |
| Payer relationship table | Product Brand to Therapeutic Class Relationship (`data/payer_data/Product_Brand_Therapeutic_Class_Relation_Dim.csv`) | Product-to-therapeutic-class mapping. |
| Payer relationship table | Product Brand to User Details Relationship (`data/payer_data/Product_Brand_User_Details_Relationship_Dim.csv`) | Product ownership/user mapping for commercial workflows. |
| Payer product table | Product Brand Dimension (`data/payer_data/Productbrand_Dim.csv`) | Product catalog, comparator identification, brand-level analytics. |
| Payer relationship table | Product Brand to Product Group Relationship (`data/payer_data/Productbrand_Productgroup_Relationship_Dim.csv`) | Product-to-group mapping and market basket enrichment. |
| Payer relationship table | Product Brand to Product NDC Relationship (`data/payer_data/Productbrand_Productndc_Relationship_Dim.csv`) | Brand-to-NDC mapping for claims/sales linkage. |
| Payer relationship table | Product Brand to Therapeutic Area Relationship (`data/payer_data/Productbrand_Therapeuticarea_Relationship_Dim.csv`) | Product-to-therapeutic-area mapping and competitor discovery. |
| Payer product table | Product Group Dimension (`data/payer_data/Productgroup_Dim.csv`) | Product grouping, portfolio/market basket analysis. |
| Payer product table | Product NDC Dimension (`data/payer_data/Productndc_Dim.csv`) | NDC-level product identity, claims/sales linking, product normalization. |
| Payer sales fact table | Sales Fact (`data/payer_data/Sales_Fact.csv`) | Sales history, market performance, commercial analytics. |
| Payer forecast fact table | Sales Forecast Fact (`data/payer_data/Sales_Forecast_Fact.csv`) | Forecasting, scenario inputs, revenue projections. |
| Payer territory table | Territory Dimension (`data/payer_data/Territory_Dim.csv`) | Territory hierarchy and field alignment. |
| Payer territory view | Territory Flatten View (`data/payer_data/Territory_Flatten_View_Dim.csv`) | Flattened territory hierarchy for reporting and joins. |
| Payer taxonomy table | Therapeutic Area Dimension (`data/payer_data/Therapeuticarea_Dim.csv`) | Therapeutic area taxonomy and indication normalization. |
| Payer taxonomy table | Therapeutic Class Dimension (`data/payer_data/Therapeuticclass_Dim.csv`) | Therapeutic class taxonomy and product grouping. |
| Payer operations table | Time off Territory Dimension (`data/payer_data/Time_off_Territory_Dim.csv`) | Field availability and territory coverage planning. |
| Payer geography table | ZIP to Territory Dimension (`data/payer_data/Zip_To_Territory_Dim.csv`) | ZIP-to-territory mapping and geographic rollups. |
| Payer category table | Category Dimension (`data/payer_data/category_dim.csv`) | Category taxonomy for payer/commercial data. |
| Payer segmentation relationship table | Decile Segmentation Relationship (`data/payer_data/decilesegmentationrelationship_dim.csv`) | Decile segmentation and targeting analytics. |
| Live trial registry API | ClinicalTrials.gov API v2 (`https://clinicaltrials.gov/api/v2`) | Public registry trial search, trial detail enrichment, fallback/benchmarking against local TrialTrove. |
| Live trial registry database | AACT / CTTI PostgreSQL (`aact-db.ctti-clinicaltrials.org`) | Structured ClinicalTrials.gov database queries, recent updates, trial detail fallback, SoA-related trial data. |
| Live trial registry API | EU CTIS public API (`https://euclinicaltrials.eu/ctis-public-api`) | EU clinical trial search and regulatory trial context. |
| Live trial registry API | ISRCTN (`https://www.isrctn.com`) | International/WHO-style trial registry lookup and additional trial IDs. |
| Live literature API | PubMed E-utilities (`https://eutils.ncbi.nlm.nih.gov/entrez/eutils`) | Literature search, evidence synthesis, publication support for rationale/regulatory strategy. |
| Live literature API | PubMed Central OAI (`https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi`) | PMC metadata/full-text discovery support where available. |
| Live ontology API | NCBO BioPortal / BioOntology (`https://data.bioontology.org`) | Medical term and ontology lookup, concept normalization, disease/procedure terminology support. |
| Live publication graph API | OpenAlex (`https://api.openalex.org`) | Publication metadata, citation graph, institutions, bibliometrics, investigator/site evidence. |
| Live DOI metadata API | Crossref (`https://api.crossref.org`) | DOI resolution, journal/publisher metadata, publication traceability. |
| Live organization registry API | ROR (`https://api.ror.org`) | Research organization IDs, institution disambiguation, parent/child organization relationships. |
| Live grant API | NIH RePORTER (`https://api.reporter.nih.gov`) | Grant-funded sites, PI funding context, development landscape, trial-grant linkage signals. |
| Live provider registry API | CMS NPI Registry / NPPES (`https://npiregistry.cms.hhs.gov/api`) | Investigator/site organization verification, NPI lookup, taxonomy/provider enrichment. |
| Live CMS facility API | CMS Open Data (`https://data.cms.gov`) | CMS facility/provider characteristics, hospitals and FQHC enrollment-style datasets. |
| Live transparency API | CMS Open Payments (`https://openpaymentsdata.cms.gov`) | Sunshine/transfers-of-value data, transparency context, physician/company relationship signals. |
| Live regulatory API | OpenFDA (`https://api.fda.gov`) | Drugs@FDA, labeling, enforcement, adverse event and safety/regulatory signals. |
| Live regulatory data feed | EMA Public JSON Feeds (`https://www.ema.europa.eu/en/documents/report`) | EU medicines, EPAR documents, guidance, orphan, shortages, referrals, post-authorization context. |
| Live regulatory FHIR API | EMA ePI FHIR (`https://epi.ema.europa.eu`) | Electronic product information lookup and EU label/SmPC-style context where enabled. |
| Optional regulatory FHIR API | EMA PMS Read (`EMA_PMS_BASE_URL`) | Optional EMA PMS medicinal product read/enrichment when configured. |
| Live regulatory web search | CDE / NMPA / China official web via Google CSE | China regulatory guidances, announcements, NMPA/CDE service notices, official portal evidence. |
| Live regulatory/compliance API | FDA Data Dashboard (`https://api-datadashboard.fda.gov/v1`) | FDA inspections and import refusals; compliance/site/manufacturer signal when credentials are configured. |
| Live web search API | Google Custom Search (`https://www.googleapis.com/customsearch/v1`) | Real-time web/guidance/news discovery, regulatory horizon scanning, source-finding for agents. |
| Web pricing source | GoodRx (`https://www.goodrx.com`) | US retail drug price and coupon context, asset pricing and commercial assumptions. |
| Composite analytics agent | Healthcare Analytics Agent | Combines claims and payer data for utilization, cost trends, patient population analytics, and commercial/RWD insights. |
| Composite planning agent | Site Map Agent | Combines TrialTrove, SiteTrove, claims, ZIP/geocode logic, and coverage calculations for site map feasibility. |
| Composite protocol agent | Protocol Authoring Agent | Uses selected TrialTrove/reference-trial data plus study context to generate protocol sections, objectives, endpoints, criteria, design, schema, and SoA. |
| Composite extraction agent | SoA Extractor Agent | Extracts schedule-of-activities tables and protocol table content for procedure/cost mapping. |
| Composite simulation agent | Simulation Agent | Generates enrollment, startup, risk, budget, and timeline projections from study design, sites, and eligibility assumptions. |
| Composite strategy agent | Asset Strategy Agent | Routes strategy questions to GoodRx, Google Search, PubMed, TrialTrove, FDA Labels, and other graph agents. |
| Composite insights agent | Insights Agent | Generates portfolio/study insights from app context and available data sources. |
| LLM synthesis source | LLM Agent | Synthesizes evidence and generated content from selected sources; not a primary data source by itself. |
| Documented future/site DB ETL source | FDA BMIS / Form 1572 | Future/site database enrichment for PI/site legal names, aliases, investigator attestations, and NPI resolution. |
| Documented future/site DB ETL source | FDA Inspections | Future/site database enrichment for site inspection history and compliance risk. |
| Documented future/site DB ETL source | FDA Mammography MQSA | Future facility certification context for imaging/mammography-capable sites. |
| Documented future/site DB ETL source | OHRP | Future IRB/human-subjects registration signals and institutional compliance context. |
| Documented future/site DB ETL source | CMS CLIA | Future lab certification enrichment for site/lab capability assessment. |
| Documented future/site DB ETL source | CMS Hospital / HPT / POS | Future facility type, hospital compare, health provider taxonomy, and place-of-service enrichment. |
| Documented future/site DB ETL source | CMS MRF | Future machine-readable pricing support for procedure/cost benchmarking where modeled. |
| Documented future/site DB ETL source | SRTR | Future transplant program outcomes and transplant-center capability signals. |
| Documented future/site DB ETL source | AABB | Future blood/cellular therapy accreditation context. |
| Documented future/site DB ETL source | CAP Directory | Future lab accreditation and diagnostic capability context. |
| Documented future/site DB ETL source | NCI Capability Sources | Future cancer center and oncology capability signals. |
| Documented future/site DB ETL source | Site URL from ROR | Future site website discovery and organization enrichment using ROR. |
