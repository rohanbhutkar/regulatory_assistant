# Study Designer / Feasibility Tool Data Needs

This organizes the data needs implied by the Study Designer workflow, especially the feasibility-oriented parts: reference trial selection, eligibility, site feasibility, enrollment simulation, and budget.

## 1. Study Setup / Core Context

Purpose: establish the minimum study context used by every downstream module.

| Data Need | Key Fields | Primary Use | Current Source / Owner |
| --- | --- | --- | --- |
| Study identity | indication, therapeutic area, phase, molecule / drug name, study title | Seed protocol generation, search, feasibility, and AI recommendations | Manual entry in Basic Info; can be inferred from selected reference trials |
| Study planning assumptions | target patient count, study duration, target site count, study design type, primary endpoint | Drives site feasibility, simulation, budget, schema, and SoA | Manual entry in Basic Info; can be updated by AI insights or generated design |
| Scientific context | objectives, background / rationale | Used for protocol sections and AI generation prompts | Manual entry; generated from reference trials |
| Study design object | study type, total participants, duration, arms, intervention names, participants per arm | Defines operational design and schema | Overall Design tab; AI-generated from selected trials |

## 2. Reference Trial Data

Purpose: benchmark the new study against similar historical or ongoing studies.

| Data Need | Key Fields | Primary Use | Current Source / Owner |
| --- | --- | --- | --- |
| Trial identifiers | Trial ID, Protocol / Trial ID, NCT ID, record URL | Traceability, citations, external review | TrialTrove / ClinicalTrials.gov-derived fields |
| Trial descriptors | title, phase, status, therapeutic area, disease, patient segment, MeSH term, ICD-10 code | Similarity search and cohort framing | TrialTrove |
| Sponsor / collaborator | sponsor, role, sponsor type, sponsor HQ country / state / city | Comparator selection and precedent review | TrialTrove |
| Intervention data | primary tested drug, other tested drugs, mechanism of action, target, therapeutic class, drug type | Drug-class benchmarking and rationale | TrialTrove |
| Objective / endpoint data | trial objective, primary endpoint, endpoint groups, endpoint details, secondary / other endpoints | Objective and endpoint generation | TrialTrove |
| Timing and enrollment data | start date, enrollment duration, enrollment close, treatment duration, primary completion, full completion, endpoints reported date | Feasibility benchmarks and simulation priors | TrialTrove |
| Enrollment performance | target accrual, actual accrual, actual as percent of target, patients per site per month | Enrollment rate, site count, and timeline assumptions | TrialTrove |
| Eligibility data | patient population, inclusion criteria, exclusion criteria, gender, age group, min / max age | IE criteria generation and feasibility funnel | TrialTrove |
| Geography and site footprint | reported sites, identified sites, trial region, countries, country count, ClinicalTrials.gov locations / site count | Site strategy and country/site allocation | TrialTrove + ClinicalTrials.gov location fields |
| Trial operations | treatment plan, study keywords, study design, decentralized trial attributes, associated CRO | Design, SoA, operational feasibility | TrialTrove |
| Evidence and audit trail | trial results, outcomes, outcome details, notes, supporting URLs, last modified, last full review | Rationale, reviewability, citation support | TrialTrove |

## 3. Protocol Content Data

Purpose: generate and maintain protocol-facing design sections.

| Section | Data Needed | Inputs Used | Output Stored |
| --- | --- | --- | --- |
| Title | phase, indication, drug name, selected reference trials | Basic Info + selected trials | full title, short title, protocol number, version |
| Rationale | disease background, unmet need, treatment landscape, MoA, prior clinical experience, endpoint/design rationale | Basic Info + selected trials + research agent | rationale section text |
| Introduction / Background / Hypothesis | indication, therapeutic area, phase, drug, selected trial evidence | Basic Info + selected trials | protocol section text |
| Objectives | primary / secondary objective patterns from selected trials | Basic Info + selected trials | objective list by type |
| Endpoints | endpoint names, definitions, timepoints, endpoint grouping | Basic Info + selected trials | endpoint list by type |
| Overall Design | study type, participants, duration, arms, interventions, allocation | Basic Info + selected trials | structured study design object |
| Schema | study duration, number of arms, study type, participant count, generated schema narrative | Overall Design + selected trials | schema text and visual diagram inputs |

## 4. Eligibility / Population Feasibility

Purpose: understand how inclusion and exclusion criteria affect eligible population and screen failure.

| Data Need | Key Fields | Primary Use | Current Source / Owner |
| --- | --- | --- | --- |
| Inclusion criteria | text, order, enabled state, extracted ICD codes, primary ICD, ICD description | Defines eligible population funnel | AI-generated from selected trials; manual edits |
| Exclusion criteria | text, order, enabled state, extracted ICD codes, primary ICD, ICD description | Defines exclusions and screen-out logic | AI-generated from selected trials; manual edits |
| Criterion impact | estimated impact, relative impact, patients affected, population before / after, impact reasoning | Eligibility funnel and simulation inputs | Claims analysis endpoint where available; fallback heuristic |
| Population baseline | indication-level / therapeutic-area population estimate | Starting population for feasibility funnel | Current heuristic by indication / TA; claims data when ICD is available |
| Claims-backed population | total patients in claims, extrapolated US patients, geography, demographics, reasoning | Real-world prevalence and screenability | Claims Data via ICD population analysis |
| Context-aware modifiers | cancer type, metastatic disease, prior therapy, biomarker selection, ECOG / CNS mets / prior therapy patterns | Adjusts criterion impact based on already-applied criteria | Frontend heuristic logic |

## 5. Schedule of Activities / Procedure Data

Purpose: turn the study design into visits, activities, and costable procedures.

| Data Need | Key Fields | Primary Use | Current Source / Owner |
| --- | --- | --- | --- |
| Visit schedule | visit ID, visit name, week, visit window | SoA table, protocol schema, budget timing | Auto-generated from duration; AI-generated from reference trials; manual edits |
| Activities | activity ID, category, name, visit applicability matrix | SoA table and CPP mapping | Default list; AI-generated from reference trials; manual edits |
| Procedure mapping | original procedure text, mapped code, mapped name, confidence score, category, alternatives | Cost per procedure and budget traceability | CPP procedure reference + fuzzy matching |
| Procedure reference catalog | code, name, description | User correction of mappings | CPP procedures endpoint |

## 6. Site Feasibility / Site Selection

Purpose: identify and select sites based on historical trial performance, location, patient access, and reference-trial precedent.

| Data Need | Key Fields | Primary Use | Current Source / Owner |
| --- | --- | --- | --- |
| Site identity | site ID, site name, organization, organization type, parent organization, record URL | Selection, export, and saved site list | SiteTrove |
| Site location | city, state, country, region, latitude, longitude, address, postal code | Map view, geographic coverage, state/country filters | SiteTrove |
| Site contact | phones, faxes, supporting URLs | Operational handoff | SiteTrove |
| Historical performance | historical trials, total trials, ongoing trials, planned trials, matching trials, total investigators, last trial start date | Ranking, filters, recommended sites | SiteTrove |
| Enrollment performance | average enrollment, average patients/site/month | Enrollment feasibility and simulation inputs | SiteTrove |
| Trial mix | disease areas, therapeutic areas, sponsors, recent trials | Fit to selected indication and trial class | SiteTrove |
| Trial-status mix | planned/open/closed/terminated/completed percentages | Operational capacity and risk filters | SiteTrove |
| SDOH / demographic access | household income, education level, insurance coverage, unemployment rate, vehicle ownership | Patient-access and diversity filters | Site map / filter data |
| Reference-trial site benchmark | average reported / identified site count across selected reference trials | "Select recommended" site count target | Selected TrialTrove trials |
| Saved selected sites | normalized ID, name, location, coordinates, score, historical performance, estimated enrollment | Simulation and budget inputs | Site Selection tab context |

## 7. Enrollment Simulation / Operational Feasibility

Purpose: estimate enrollment curve, timelines, risk, budget pressure, and completion probability.

| Data Need | Key Fields | Primary Use | Current Source / Owner |
| --- | --- | --- | --- |
| Simulation parameters | enrollment target, timeline months, screen failure rate, dropout rate | Monte Carlo simulation inputs | Manual entry; AI-drafted from context |
| Study context for simulation | phase, therapeutic area, indication, reference trial enrollment, duration, sites, patients/site/month | Priors for simulation configuration | Basic Info + selected trials |
| Selected site inputs | site ID/name, state, country, historical trials, ongoing trials, average enrollment, organization type | Site activation and enrollment assumptions | Saved selected sites |
| Population inputs | total population, final eligible population, US population, TA population, population by state | Enrollment pool and geography constraints | IE criteria funnel + selected site geography |
| Advanced options | advanced simulation flag, total budget, country modeling, budget constraints, regulatory events, operational constraints, external shocks | Optional risk modeling | Simulation tab inputs |
| Simulation outputs | enrollment curve, milestones, risk factors, risk assessment, success probability, expected completion date, expected duration | Decision support and saved study state | Simulation backend |
| Budget-related outputs | budget projection, cost per patient, monthly burn, budget exhaustion probability | Budget integration | Simulation backend |
| Operational outputs | country performance, regulatory event summary, CRA/DM utilization, queries per site, monitoring coverage | Operational feasibility assessment | Advanced simulation backend |
| Model assumptions | iterations, target enrollment, number of sites/countries, site parameters, global parameters, learning curve, seasonal effects, stochastic variation, data sources | Auditability and explainability | Simulation backend |

## 8. Budget / Cost Feasibility

Purpose: estimate study cost with patient, site, operational, overhead, contingency, country, and timeline views.

| Data Need | Key Fields | Primary Use | Current Source / Owner |
| --- | --- | --- | --- |
| Budget context | indication, phase, therapeutic area | CPP and overhead rules | Basic Info |
| Study design inputs | total participants, duration months, arms | Patient costs, operational duration, allocation-sensitive costs | Overall Design + study context |
| IE criteria | inclusion / exclusion criteria and impacts | Screen failure and patient-cost assumptions | IE Criteria tab |
| Endpoints | endpoint list | Procedure and assessment intensity | Endpoints tab |
| SoA data | visits, activities, visit-activity matrix | Procedure mapping and line-level costs | SoA tab |
| Procedure mappings | mapped procedure codes and alternatives | Per-procedure cost calculation | CPP procedure references |
| Selected sites | site name, country, patients per site | Site costs, country allocation | Site Selection tab |
| Simulation results | expected duration, enrollment curve | Timeline and cashflow | Simulation tab |
| CPP reference data | clinical procedure costs, OPAL, SPU, drug costs, country specifications, indication and overhead rules | Budget calculation | CPP datasets |
| Budget outputs | grand total, patient costs, site costs, operational costs, overhead, contingency, timeline cashflow | Feasibility summary and export | Budget backend |
| Export package | summary, cost breakdowns, procedure mappings, country allocation, timeline | Stakeholder handoff | Budget Export Manager |

## 9. External / Cataloged Data Sources

For the single integrated table of all local, live, composite, and documented future sources, see `docs/DATA_SOURCE_USAGE_TABLE.md`.

| Source | Current Role | Main Study Designer Consumers |
| --- | --- | --- |
| TrialTrove | Proprietary clinical trial database | Reference Trials, protocol generation, simulation priors |
| SiteTrove | Site location and performance database | Site Selection, site filters, site export, simulation |
| Claims Data | Healthcare claims data for utilization and patient population | IE impact, ICD population analysis, population funnel |
| FDA Structured Labels | Drug label structure, indications, MoA, subpopulations | Research / regulatory support, rationale |
| PubMed | Medical publication evidence | Rationale, background, evidence synthesis |
| OpenFDA | FDA drug and safety data | Safety/regulatory context |
| EMA / EU medicines | EU regulatory medicine information | Regulatory context |
| CDE / NMPA | China regulatory web evidence | Regulatory context |
| CPP Clinical Procedures | Procedure reference costs | SoA-to-cost mapping and patient costs |
| CPP OPAL | Operational workload formulas | OPAL and operational budget |
| CPP SPU / Drug Costs / Country Specs | Pricing, country, and market rules | Country allocation and market/cost assumptions |
| Payer / Formulary / Product / Geography dimensions | Commercial and market access context | Broader commercial analysis and potential future feasibility overlays |

## 10. Cross-Cutting Requirements

| Need | Why It Matters |
| --- | --- |
| Source traceability | Generated content should retain which trials, claims analyses, site records, or references informed it. |
| Refresh date / version | Trial, site, claims, CPP, and regulatory data should carry last refresh or extraction date. |
| Confidence and fallback labeling | Distinguish claims-backed estimates from heuristic estimates and AI-generated assumptions. |
| User override history | Manual edits to criteria, endpoints, sites, procedure mappings, and simulation parameters should be tracked. |
| Normalized identifiers | Keep TrialTrove IDs, NCT IDs, SiteTrove IDs, ICD-10 codes, procedure codes, product IDs, and country codes cleanly separated. |
| Export-ready data model | The same data should support USDM export, budget exports, site CSVs, and protocol section outputs. |
| Dependency ordering | Basic Info + Reference Trials feed most AI generation; IE + Site Selection feed Simulation; SoA + Sites + Simulation feed Budget. |

## Suggested Build / Review Order

1. Lock the core study context fields and validation rules.
2. Normalize TrialTrove and SiteTrove field mappings with stable identifiers.
3. Separate generated assumptions from source-backed evidence.
4. Add a visible data provenance layer for each module.
5. Define the export schema for Study Design, Site Feasibility, Simulation, Budget, and USDM.
6. Backfill missing source metadata: refresh date, coverage, quality score, and owner.
