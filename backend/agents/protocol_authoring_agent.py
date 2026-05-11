"""
Enhanced Protocol Authoring Agent for Clinical Research Assistant
Comprehensive protocol generation with full TrialTrove data extraction and section-specific prompts
"""
import asyncio
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from models.schemas import ClinicalTrialResult
from config import settings
from utils.logger import log_error
from utils.cache import cache_manager
from agents.llm_agent import llm_agent

class ProtocolAuthoringAgent:
    """Enhanced agent for generating clinical trial protocol components with full TrialTrove integration"""
    
    def __init__(self):
        self.client = llm_agent.client
        
        # Comprehensive mapping of TrialTrove columns to use in each section
        self.section_configs = {
            'title': {
                'system_prompt': """You are an expert in creating protocol titles for clinical trials. 
Your titles must be complete, descriptive, and follow ICH GCP guidelines.

CRITICAL: Follow the exact output format specified below. The frontend parser expects this structure.""",
                'relevant_columns': [
                    'Trial_Title', 'Trial_Phase', 'Study_Design', 'Disease', 'Patient_Population',
                    'Primary_Tested_Drug', 'Other_Tested_Drug', 'Trial_Objective', 'Primary_Endpoint'
                ],
                'output_format': """REQUIRED FORMAT (frontend parser expects this exact structure):

**FULL TITLE:**
A Phase [X], Randomized, Double-Blind, Placebo-Controlled, Multicenter Study to Evaluate the Efficacy and Safety of [Drug Name] in Combination with [Other Drug] versus [Comparator] in Patients with [Specific Condition and Stage]

**SHORT TITLE:**
Phase [X] [Disease Abbreviation] Study

RULES:
- Use "**FULL TITLE:**" header (can use FULL TITLE: or **FULL TITLE:**)
- Use "**SHORT TITLE:**" header (can use SHORT TITLE: or **SHORT TITLE:**)
- Full title must be complete on following lines (can span multiple lines)
- Short title must be on following lines
- Full title should include:
  * Study phase
  * Design elements (Randomized, Double-Blind, Placebo-Controlled, etc.)
  * Primary objective
  * Intervention(s) being tested
  * Specific patient population
- Full title: 150-250 characters
- Short title: 30-60 characters
- Use standard medical abbreviations for short title
- NO markdown headers (# ## ###) in the title itself"""
            },
            
            'introduction': {
                'system_prompt': """You are an expert in writing introductions for clinical trial protocols.
Focus on providing context for the trial, establishing the medical and scientific background.""",
                'relevant_columns': [
                    'Disease', 'Therapeutic_Area', 'MeSH_Term', 'Patient_Population', 'Patient_Segment',
                    'Primary_Tested_Drug', 'Primary_Tested_Drug_Mechanism_Of_Action', 'Primary_Tested_Drug_Target',
                    'Primary_Tested_Drug_Therapeutic_Class', 'Trial_Objective', 'Study_Design'
                ],
                'output_format': """Write a comprehensive introduction (300-400 words) with these sections:

1. **Disease Overview** (1 paragraph)
   - Epidemiology and burden
   - Clinical manifestations
   - Current treatment gaps

2. **Investigational Product** (1 paragraph)
   - Drug mechanism of action
   - Target and therapeutic class
   - Rationale for development

3. **Study Overview** (1 paragraph)
   - Primary objective
   - Study design overview
   - Expected contribution to field

Include specific data points from reference trials (enrollment numbers, endpoints, results where available).
Use scientific language appropriate for regulatory submission."""
            },
            
            'rationale': {
                'system_prompt': """You are an expert in writing rationales for clinical trials.
The rationale should justify why this trial is necessary and what scientific questions it addresses.""",
                'relevant_columns': [
                    'Disease', 'Primary_Tested_Drug', 'Primary_Tested_Drug_Mechanism_Of_Action',
                    'Primary_Tested_Drug_Target', 'Trial_Objective', 'Study_Design', 'Treatment_Plan',
                    'Primary_Endpoint_Details', 'Secondary_Other_Endpoint_Details', 'Trial_Results',
                    'Prior_Concurrent_Therapy', 'Trial_Outcomes'
                ],
                'output_format': """Write a comprehensive rationale (400-500 words) addressing:

1. **Unmet Medical Need** (1-2 paragraphs)
   - Current standard of care limitations
   - Evidence from reference trials showing gaps
   - Patient population affected

2. **Scientific Rationale** (1-2 paragraphs)
   - Mechanism of action and its relevance to disease
   - Preclinical and early clinical evidence
   - How this addresses the unmet need

3. **Study Design Rationale** (1 paragraph)
   - Why this design is appropriate
   - Justification for endpoints chosen
   - Expected clinical benefit

Reference specific trials from the provided data with their outcomes."""
            },
            
            'background': {
                'system_prompt': """You are an expert in writing comprehensive background sections for protocols.
Provide detailed scientific and clinical context for the trial.""",
                'relevant_columns': [
                    'Disease', 'Therapeutic_Area', 'MeSH_Term', 'Patient_Population', 'Patient_Segment',
                    'Primary_Tested_Drug', 'Primary_Tested_Drug_Mechanism_Of_Action', 'Primary_Tested_Drug_Target',
                    'Primary_Tested_Drug_Therapeutic_Class', 'Other_Tested_Drug', 'Other_Tested_Drug_Mechanism_Of_Action',
                    'Oncology_Biomarker', 'Prior_Concurrent_Therapy', 'Trial_Results', 'Trial_Outcomes'
                ],
                'output_format': """Write a detailed background (600-800 words) covering:

1. **Disease Background** (2 paragraphs)
   - Pathophysiology and etiology
   - Epidemiology with specific statistics
   - Disease classification and patient segments
   - Relevant biomarkers

2. **Current Treatment Landscape** (2 paragraphs)
   - Standard of care approaches
   - Treatment guidelines and recommendations
   - Limitations and adverse effects
   - Prior/concurrent therapies used in reference trials

3. **Investigational Product(s)** (2-3 paragraphs)
   - Detailed mechanism of action
   - Target specificity
   - Pharmacokinetics and pharmacodynamics
   - Development history and prior studies
   - Comparative analysis with other agents

4. **Clinical Evidence** (1-2 paragraphs)
   - Summary of key reference trial results
   - Efficacy and safety data
   - Dose-finding studies
   - Relevant biomarker data

Include citations to specific trials from the reference data."""
            },
            
            'hypothesis': {
                'system_prompt': """You are an expert in formulating clinical trial hypotheses.
Hypotheses must be testable, specific, and directly linked to endpoints.""",
                'relevant_columns': [
                    'Primary_Tested_Drug', 'Disease', 'Trial_Objective', 'Study_Design',
                    'Primary_Endpoint', 'Primary_Endpoint_Details', 'Secondary_Other_Endpoint',
                    'Secondary_Other_Endpoint_Details', 'Treatment_Plan', 'Patient_Population'
                ],
                'output_format': """Generate 2-3 specific hypotheses:

**Primary Hypothesis:**
[Drug X] will demonstrate [specific improvement] compared to [control/comparator] as measured by [primary endpoint] in patients with [specific condition].

**Secondary Hypotheses:**
1. [Drug X] will show [specific secondary outcome]...
2. [Safety/tolerability hypothesis]...

Requirements for each hypothesis:
- Specific, measurable outcome
- Clear comparator (if applicable)
- Timepoint for assessment
- Statistical approach (superiority/non-inferiority/equivalence)
- Based on reference trial data and expected effect sizes

Include expected effect sizes from reference trials where available."""
            },
            
            'primary_objectives': {
                'system_prompt': """You are an expert in defining primary objectives for clinical trials.
Objectives must be precise, measurable, and aligned with regulatory requirements.

CRITICAL: Follow the exact output format specified below. The frontend parser expects this structure.""",
                'relevant_columns': [
                    'Trial_Objective', 'Primary_Endpoint', 'Primary_Endpoint_Group', 'Primary_Endpoint_Details',
                    'Study_Design', 'Treatment_Plan', 'Disease', 'Patient_Population', 'Primary_Tested_Drug'
                ],
                'output_format': """REQUIRED FORMAT (frontend parser expects this exact structure):

**Primary Objective(s):**

1. To evaluate the efficacy of [intervention] compared to [control] as measured by [primary endpoint] in [population] over [timeframe].
2. [Second primary objective if applicable]

**Secondary Objectives:**

1. To assess [secondary outcome 1] in [population] as measured by [endpoint] at [timepoint].
2. To evaluate [secondary outcome 2]...
3. To characterize [safety/tolerability]...
4. To explore [exploratory endpoint]...

RULES:
- Use numbered lists (1. 2. 3. etc.)
- Start each objective with "To [verb]..."
- NO markdown headers (# ## ###)
- NO bullet points (use numbered lists only)
- Each objective should be a complete sentence
- Include intervention, comparison, endpoint, population, and timepoint
- Maximum 50 words per objective
- Primary: 1-2 objectives
- Secondary: 3-6 objectives"""
            },
            
            'secondary_objectives': {
                'system_prompt': """You are an expert in defining secondary objectives for clinical trials.
Secondary objectives support primary objectives and explore additional research questions.

CRITICAL: Follow the exact output format specified below. The frontend parser expects this structure.""",
                'relevant_columns': [
                    'Secondary_Other_Endpoint', 'Secondary_Other_Endpoint_Group', 'Secondary_Other_Endpoint_Details',
                    'Study_Design', 'Treatment_Plan', 'Disease', 'Patient_Population', 'Trial_Objective'
                ],
                'output_format': """REQUIRED FORMAT (frontend parser expects this exact structure):

**Secondary Objectives:**

1. To assess [secondary outcome 1] in [population] as measured by [endpoint] at [timepoint].
2. To evaluate [secondary outcome 2] compared to [control] using [measurement method].
3. To characterize the safety and tolerability profile of [intervention] in [population].
4. To explore [exploratory endpoint] and its correlation with [clinical outcome].
5. To determine [additional outcome] in subgroups defined by [criteria].

RULES:
- Use numbered lists (1. 2. 3. etc.)
- Start each objective with "To [verb]..." (assess, evaluate, characterize, explore, determine, etc.)
- NO markdown headers (# ## ###)
- NO bullet points or asterisks
- Each objective should be a complete sentence
- Include what you're measuring and how
- 3-6 objectives total
- Maximum 50 words per objective
- Reference similar objectives from reference trials"""
            },
            
            'primary_endpoints': {
                'system_prompt': """You are an expert in defining clinical trial endpoints.
Primary endpoints must be clearly defined, validated, and clinically meaningful.

CRITICAL OUTPUT FORMAT REQUIREMENTS:
1. NO section headers (###), NO numbered lists (1., 2., 3.)
2. Each endpoint MUST start with a bold name: **Endpoint Name**
3. Follow immediately with bullet points for Definition and Timepoint
4. Use EXACTLY this format (the frontend parser requires it)

DO NOT use numbered sections like "6.1" or headers like "###".
DO NOT include tables or schedules.
ONLY list individual endpoints in the exact format below.""",
                'relevant_columns': [
                    'Primary_Endpoint', 'Primary_Endpoint_Group', 'Primary_Endpoint_Details',
                    'Study_Design', 'Treatment_Duration_Mos', 'Patient_Population', 'Disease'
                ],
                'output_format': """REQUIRED FORMAT (copy this structure EXACTLY):

**Primary Endpoint(s):**

**Overall Survival (OS)**
- **Definition**: Time from randomization to death from any cause.
- **Timepoint**: Assessed continuously until study completion (minimum 24 months follow-up)

**Progression-Free Survival (PFS)**
- **Definition**: Time from randomization to first documented disease progression per RECIST v1.1 or death from any cause, whichever occurs first.
- **Timepoint**: Assessed every 8 weeks for first year, then every 12 weeks

IMPORTANT: Do NOT add section numbers, headers, or tables. ONLY list endpoints in this format

RULES:
- Start with "**Primary Endpoint(s):**" header
- Each endpoint name must be in bold on its own line: **Name (Abbreviation)**
- Follow with bullet points for Definition and Timepoint
- Use this exact format:
  - **Definition**: [Complete definition]
  - **Timepoint**: [When it's measured]
- NO numbered lists
- NO markdown headers (# ## ###)
- Use bullet points (-) ONLY for Definition and Timepoint
- Include standard medical abbreviations in parentheses
- 1-2 primary endpoints
- Each definition should be clear, measurable, and regulatory-compliant
- Reference similar endpoints from reference trials"""
            },
            
            'secondary_endpoints': {
                'system_prompt': """You are an expert in defining PRIMARY and SECONDARY endpoints for clinical trials.

CRITICAL: You MUST generate BOTH sections:
1. Primary Endpoint(s) section - with 1-2 primary endpoints
2. Secondary Endpoint(s) section - with 4-8 secondary endpoints

CRITICAL OUTPUT FORMAT REQUIREMENTS:
1. NO section headers (###), NO numbered lists (1., 2., 3.)
2. Each endpoint MUST start with a bold name: **Endpoint Name**
3. Follow immediately with bullet points for Definition and Timepoint
4. Use EXACTLY this format (the frontend parser requires it)

DO NOT use numbered sections like "8.2.1" or headers like "###".
DO NOT include tables or schedules.
ONLY list individual endpoints in the exact format below.

IMPORTANT: Generate AT LEAST 4-6 secondary endpoints covering:
- Efficacy measures (response rate, duration of response)
- Safety endpoints (adverse events, toxicity)
- Quality of life (patient-reported outcomes)
- Biomarker/exploratory endpoints (if applicable)""",
                'relevant_columns': [
                    'Secondary_Other_Endpoint', 'Secondary_Other_Endpoint_Group', 'Secondary_Other_Endpoint_Details',
                    'Study_Design', 'Treatment_Duration_Mos', 'Patient_Population', 'Disease',
                    'Oncology_Biomarker'
                ],
                'output_format': """REQUIRED FORMAT (copy this structure EXACTLY):

**Primary Endpoint(s):**

**Overall Survival (OS)**
- **Definition**: Time from randomization to death from any cause.
- **Timepoint**: Assessed continuously until study completion

**Progression-Free Survival (PFS)**
- **Definition**: Time from randomization to first documented disease progression or death from any cause.
- **Timepoint**: Assessed every 8 weeks until progression

**Secondary Endpoint(s):**

**Objective Response Rate (ORR)**
- **Definition**: Proportion of participants with complete or partial response per RECIST v1.1.
- **Timepoint**: Assessed every 8 weeks during treatment

**Duration of Response (DOR)**
- **Definition**: Time from first documented response to disease progression or death.
- **Timepoint**: Assessed every 8 weeks until progression

**Quality of Life (QoL)**
- **Definition**: Change from baseline in EORTC QLQ-C30 global health status score.
- **Timepoint**: Assessed at baseline, every 12 weeks, and end of treatment

**Safety**
- **Definition**: Incidence and severity of adverse events graded per CTCAE v5.0.
- **Timepoint**: Assessed continuously throughout treatment and 30 days post-treatment

**Pharmacokinetics (PK)**
- **Definition**: Area under the curve (AUC) and maximum concentration (Cmax) of study drug.
- **Timepoint**: Pre-dose and post-dose sampling on Cycle 1 Day 1, Day 8, and Day 15

CRITICAL REQUIREMENTS:
1. MUST include the "**Secondary Endpoint(s):**" header
2. MUST list at least 4-6 secondary endpoints after the header
3. Do NOT add section numbers, headers (###), or tables
4. ONLY list endpoints in this exact format

Remember: This API is called for BOTH primary and secondary endpoints.
Always generate the complete output with BOTH sections."""
            },
            
            'inclusion_criteria': {
                'system_prompt': """You are an expert in writing inclusion criteria for clinical trials.
Criteria must be specific, measurable, and align with the target population.

CRITICAL: Follow the exact output format specified below. The frontend parser expects this structure.""",
                'relevant_columns': [
                    'Inclusion_Criteria', 'Patient_Population', 'Patient_Segment', 'Patient_Gender',
                    'Patient_Age_Group', 'Min_Patient_Age', 'Max_Patient_Age', 'Disease',
                    'Oncology_Biomarker', 'Prior_Concurrent_Therapy', 'Study_Design'
                ],
                'output_format': """REQUIRED FORMAT (frontend parser expects this exact structure):

**Inclusion Criteria:**

1. Age ≥18 years at the time of informed consent
2. Histologically or cytologically confirmed diagnosis of [disease/condition]
3. Measurable disease per RECIST v1.1 criteria (at least one measurable lesion)
4. ECOG performance status 0-1
5. Life expectancy of at least 12 weeks in the opinion of the investigator
6. Adequate organ function as defined by laboratory values within 7 days prior to randomization
7. For women of childbearing potential: negative pregnancy test and agreement to use highly effective contraception
8. For men: agreement to use contraception during treatment and for 90 days after last dose
9. Able to swallow and retain oral medication
10. Willing and able to provide written informed consent and comply with study procedures

RULES:
- Start with "**Inclusion Criteria:**" header
- Use numbered lists (1. 2. 3. etc.)
- Each criterion should be a single, clear, actionable statement
- NO markdown headers (# ## ###)
- NO sub-bullets or nested lists
- NO category groupings (like "Demographics:", "Diagnosis:", etc.)
- 8-15 criteria total
- Be specific with numbers, timeframes, and thresholds
- Include age, diagnosis, disease characteristics, performance status, organ function, and consent
- Reference similar criteria from reference trials"""
            },
            
            'exclusion_criteria': {
                'system_prompt': """You are an expert in writing exclusion criteria for clinical trials.
Exclusion criteria protect patient safety and ensure data integrity.""",
                'relevant_columns': [
                    'Exclusion_Criteria', 'Patient_Population', 'Disease', 'Prior_Concurrent_Therapy',
                    'Oncology_Biomarker', 'Study_Design', 'Primary_Tested_Drug'
                ],
                'output_format': """REQUIRED FORMAT (frontend parser expects this exact structure):

**Exclusion Criteria:**

1. Prior systemic anticancer therapy within 4 weeks or 5 half-lives, whichever is shorter, before first dose
2. History of severe hypersensitivity reactions to monoclonal antibodies or any study drug component
3. Active or untreated brain metastases or leptomeningeal disease
4. History of another malignancy within 3 years except adequately treated basal cell or squamous cell skin cancer
5. Active autoimmune disease requiring systemic immunosuppressive therapy within 2 years
6. Active infection requiring systemic therapy
7. Pregnant or breastfeeding women
8. Known history of HIV, Hepatitis B, or Hepatitis C infection
9. Cardiac disease including unstable angina, myocardial infarction within 6 months, or symptomatic heart failure
10. Significant pulmonary disease requiring supplemental oxygen
11. Active bleeding or bleeding diathesis
12. Prior stem cell or bone marrow transplantation within 5 years
13. Concurrent use of immunosuppressive agents except for physiologic doses of corticosteroids
14. Major surgery within 4 weeks prior to first dose or planned surgery during study
15. Any condition that would interfere with the ability to comply with study procedures

RULES:
- Start with "**Exclusion Criteria:**" header
- Use numbered lists (1. 2. 3. etc.)
- Each criterion should be a single, clear, actionable statement
- NO markdown headers (# ## ###)
- NO sub-bullets or nested lists
- NO category groupings (like "Medical History:", "Prior Therapy:", etc.)
- 10-20 criteria total
- Be specific with timeframes and thresholds
- Include prior therapy, medical history, lab values, infections, pregnancy, and compliance
- Reference similar criteria from reference trials"""
            },
            
            'study_design': {
                'system_prompt': """You are an expert in describing clinical trial designs.
Provide a complete overview of the study methodology.

CRITICAL: Follow the exact output format specified below. The frontend parser expects this structure.""",
                'relevant_columns': [
                    'Study_Design', 'Trial_Phase', 'Treatment_Plan', 'Enrollment_Duration_Mos',
                    'Treatment_Duration_Mos', 'Target_Accrual', 'Study_Keywords', 'Trial_Region',
                    'Primary_Tested_Drug', 'Other_Tested_Drug', 'Trial_Title', 'Disease'
                ],
                'output_format': """CRITICAL OUTPUT FORMAT REQUIREMENTS:

The frontend parser extracts:
1. Study Type from keywords (randomized, single-arm, crossover, observational)
2. Total Participants from "N=300", "300 patients", "approximately 300 subjects"
3. Duration from "52 weeks", "24 months", etc.
4. Treatment Arms from "Arm A:", "Group 1:", "Treatment 1:" patterns

REQUIRED FORMAT:

**Study Type:** [Randomized Controlled Trial/Single-Arm Trial/Crossover Trial/Observational Study]

**Phase:** [Phase I/II/III/IV]

**Total Enrollment:** N=[exact number] patients (e.g., N=300 patients)

**Study Duration:** [X weeks/months/years] (e.g., 52 weeks)

**Design Overview:**
[1-2 sentences describing randomization, blinding, control]

**Treatment Arms:**

**Arm A: [Actual Drug Name]** (2:1 randomization if Phase II/III)
- Intervention: [Drug name] [dose] [route] [schedule]
- Participants: Approximately [2/3 of total] patients
- Duration: [X weeks/months]

**Arm B: Control** (if randomized)
- Intervention: [Placebo/Standard of care/Active comparator]
- Participants: Approximately [1/3 of total] patients  
- Duration: [X weeks/months]

NOTE: For Phase I trials, typically use single-arm design.

**Study Procedures:**
- Screening: [duration]
- Treatment: [duration]
- Follow-up: [duration]

**Key Assessments:**
- Primary endpoint assessment timing
- Safety monitoring frequency
- PK/PD sampling (if applicable)

**Randomization Details:** (if applicable)
- Ratio: [e.g., 2:1]
- Stratification: [factors if applicable]
- Blinding: [Double-blind/Open-label/etc.]

CRITICAL RULES:
1. ALWAYS specify exact drug names from Primary_Tested_Drug (not "investigational drug")
2. ALWAYS provide exact participant counts that sum to total
3. For Phase II/III randomized trials, use 2:1 ratio (treatment:control)
4. Use "N=[number] patients" format for enrollment
5. Use "Arm A:", "Arm B:" headers for treatment arms
6. Specify participant numbers per arm that add up to total
7. Extract actual drug names from reference trials

Reference similar designs from reference trials, extracting actual drug names and enrollment numbers."""
            },
            
            'schedule_of_activities': {
                'system_prompt': """You are an expert in creating Schedule of Activities (SoA) for clinical trials.
The SoA must comprehensively list all study procedures and their timing.

CRITICAL: Generate an actual markdown table, not a narrative description. The frontend parser expects this exact structure.""",
                'relevant_columns': [
                    'Study_Design', 'Treatment_Duration_Mos', 'Primary_Endpoint_Details',
                    'Secondary_Other_Endpoint_Details', 'Treatment_Plan', 'Enrollment_Duration_Mos'
                ],
                'output_format': """REQUIRED FORMAT (frontend parser expects this exact markdown table structure):

Generate a markdown table with this structure:

| Procedure/Assessment | Screening | Baseline | Week 4 | Week 8 | Week 12 | End of Treatment | Follow-up |
|---------------------|-----------|----------|---------|---------|----------|-----------------|-----------|
| Informed Consent | X | | | | | | |
| Inclusion/Exclusion Criteria | X | | | | | | |
| Demographics | X | | | | | | |
| Medical History | X | | | | | | |
| Physical Examination | X | X | X | X | X | X | X |
| Vital Signs | X | X | X | X | X | X | X |
| ECG | X | X | | X | | X | X |
| Hematology | X | X | X | X | X | X | X |
| Blood Chemistry | X | X | X | X | X | X | X |
| Tumor Assessment (if oncology) | X | X | | X | X | X | |
| Disease Assessment | X | X | X | X | X | X | X |
| Adverse Event Assessment | | X | X | X | X | X | X |
| Concomitant Medications | X | X | X | X | X | X | X |
| Performance Status | X | X | X | X | X | X | |
| Quality of Life | X | X | | X | | X | |
| PK Blood Samples | | X | X | X | X | | |
| Biomarker Samples | X | X | | X | | X | |
| Study Drug Dispensing | | X | X | X | X | | |
| Study Drug Accountability | | | X | X | X | X | |

RULES:
1. Use markdown table format with | separators
2. First row: column headers with visit names
3. Include separator row with dashes
4. Each row: one procedure/assessment
5. Mark required procedures with "X"
6. Leave cells empty if procedure not required at that visit
7. Visit columns should match the treatment duration and phase
8. Include these visit columns (adjust based on treatment duration):
   - Screening (Week -2)
   - Baseline (Week 0/Day 1)
   - Treatment visits (Week 2, 4, 8, 12, etc.)
   - End of Treatment
   - Follow-up visits

CATEGORIES TO INCLUDE:
- Administrative (consent, eligibility, demographics)
- Safety (vitals, ECG, labs, AEs)
- Disease Assessment (imaging, performance status)
- Efficacy (endpoint measurements, QoL)
- Pharmacokinetics/Biomarkers
- Study Drug Management

Use reference trials to determine appropriate visit schedule and procedures."""
            },
            
            'schema': {
                'system_prompt': """You are an expert in creating study schema diagrams for clinical trials.
The schema should visually represent the study flow and key decision points.""",
                'relevant_columns': [
                    'Study_Design', 'Trial_Phase', 'Treatment_Plan', 'Target_Accrual',
                    'Treatment_Duration_Mos', 'Enrollment_Duration_Mos'
                ],
                'output_format': """Describe a study schema diagram in detail (text-based representation):

**Study Schema Structure:**

1. **Screening Phase** (Day -28 to Day -1)
   - Key screening procedures
   - Eligibility confirmation

2. **Randomization** (Day 1)
   - Stratification factors
   - Treatment assignment

3. **Treatment Phase** (Day 1 to Week X)
   For each arm:
   - Treatment regimen
   - Cycle length
   - Number of cycles
   - Key assessment points

4. **End of Treatment**
   - Completion criteria
   - Final assessments

5. **Follow-up Phase**
   - Safety follow-up duration
   - Survival follow-up (if applicable)
   - Long-term assessments

6. **Key Decision Points:**
   - Dose modifications
   - Treatment discontinuation criteria
   - Safety stopping rules

Format as a clear textual description that could be converted to a visual diagram.
Include patient flow numbers and dropout expectations from reference trials.
Maximum 500 words."""
            }
        }
        
        # Store authored sections for context
        self.authored_sections = {}

    def _extract_trialtrove_fields(self, trial: Any) -> Dict[str, Any]:
        """
        Comprehensive extraction of all TrialTrove fields from trial data
        Handles both ClinicalTrialResult objects and raw dictionaries
        """
        # Convert to dict if it's an object
        if hasattr(trial, 'dict'):
            t = trial.dict()
        elif hasattr(trial, '__dict__'):
            t = trial.__dict__
        elif isinstance(trial, dict):
            t = trial
        else:
            t = {}
        
        # Extract metadata if available
        metadata = t.get('metadata', {})
        if isinstance(metadata, dict):
            # Merge metadata fields into main dict for easier access
            t = {**t, **metadata}
        
        # Comprehensive field mapping from TrialTrove structure
        fields = {
            # Core identifiers
            'Trial_ID': self._get_field(t, ['Trial_ID', 'Trial ID', 'trial_id', 'nct_id', 'NCTId']),
            'Protocol_Trial_ID': self._get_field(t, ['Protocol_Trial_ID', 'Protocol/Trial ID', 'protocol_id']),
            'Trial_Title': self._get_field(t, ['Trial_Title', 'Trial Title', 'title', 'brief_title']),
            
            # Phase and status
            'Trial_Phase': self._get_field(t, ['Trial_Phase', 'Trial Phase', 'phase', 'Phase']),
            'Trial_Status': self._get_field(t, ['Trial_Status', 'Trial Status', 'status', 'Status']),
            
            # Disease and therapeutic area
            'Therapeutic_Area': self._get_field(t, ['Therapeutic_Area', 'Therapeutic Area', 'therapeutic_area']),
            'Disease': self._get_field(t, ['Disease', 'disease', 'condition', 'Condition']),
            'Patient_Segment': self._get_field(t, ['Patient_Segment', 'Patient Segment', 'patient_segment']),
            'MeSH_Term': self._get_field(t, ['MeSH_Term', 'MeSH Term', 'mesh_term']),
            'Trial_ICD_10_Code': self._get_field(t, ['Trial_ICD_10_Code', 'Trial ICD-10 Code', 'icd_10_code']),
            
            # Sponsor information
            'Sponsor_Collaborator': self._get_field(t, ['Sponsor_Collaborator', 'Sponsor/Collaborator', 'sponsor', 'Sponsor']),
            'Sponsor_Collaborator_Role': self._get_field(t, ['Sponsor_Collaborator_Role', 'Sponsor/Collaborator Role']),
            'Sponsor_Collaborator_Type': self._get_field(t, ['Sponsor_Collaborator_Type', 'Sponsor/Collaborator Type']),
            
            # Drug information - Primary
            'Primary_Tested_Drug': self._get_field(t, ['Primary_Tested_Drug', 'Primary Tested Drug', 'intervention', 'Intervention']),
            'Primary_Tested_Drug_Mechanism_Of_Action': self._get_field(t, ['Primary_Tested_Drug_Mechanism_Of_Action', 'Primary Tested Drug: Mechanism Of Action']),
            'Primary_Tested_Drug_Target': self._get_field(t, ['Primary_Tested_Drug_Target', 'Primary Tested Drug: Target']),
            'Primary_Tested_Drug_Therapeutic_Class': self._get_field(t, ['Primary_Tested_Drug_Therapeutic_Class', 'Primary Tested Drug: Therapeutic Class']),
            'Primary_Tested_Drug_Drug_Type': self._get_field(t, ['Primary_Tested_Drug_Drug_Type', 'Primary Tested Drug: Drug Type']),
            
            # Drug information - Other
            'Other_Tested_Drug': self._get_field(t, ['Other_Tested_Drug', 'Other Tested Drug']),
            'Other_Tested_Drug_Mechanism_Of_Action': self._get_field(t, ['Other_Tested_Drug_Mechanism_Of_Action', 'Other Tested Drug: Mechanism Of Action']),
            'Other_Tested_Drug_Target': self._get_field(t, ['Other_Tested_Drug_Target', 'Other Tested Drug: Target']),
            'Other_Tested_Drug_Therapeutic_Class': self._get_field(t, ['Other_Tested_Drug_Therapeutic_Class', 'Other Tested Drug: Therapeutic Class']),
            
            # Biomarkers
            'Oncology_Biomarker': self._get_field(t, ['Oncology_Biomarker', 'Oncology Biomarker', 'biomarker']),
            'Oncology_Biomarker_Common_Uses': self._get_field(t, ['Oncology_Biomarker_Common_Uses', 'Oncology Biomarker Common Use(s)']),
            
            # Objectives and endpoints
            'Trial_Objective': self._get_field(t, ['Trial_Objective', 'Trial Objective', 'objective', 'description', 'brief_description']),
            'Primary_Endpoint': self._get_field(t, ['Primary_Endpoint', 'Primary Endpoint', 'primary_endpoint']),
            'Primary_Endpoint_Group': self._get_field(t, ['Primary_Endpoint_Group', 'Primary Endpoint Group']),
            'Primary_Endpoint_Details': self._get_field(t, ['Primary_Endpoint_Details', 'Primary Endpoint Details']),
            'Secondary_Other_Endpoint': self._get_field(t, ['Secondary_Other_Endpoint', 'Secondary/Other Endpoint', 'secondary_endpoint']),
            'Secondary_Other_Endpoint_Group': self._get_field(t, ['Secondary_Other_Endpoint_Group', 'Secondary/Other Endpoint Group']),
            'Secondary_Other_Endpoint_Details': self._get_field(t, ['Secondary_Other_Endpoint_Details', 'Secondary/Other Endpoint Details']),
            
            # Timeline information
            'Start_Date': self._get_field(t, ['Start_Date', 'Start Date', 'start_date', 'study_start_date']),
            'Enrollment_Duration_Mos': self._get_field(t, ['Enrollment_Duration_Mos', 'Enrollment Duration (Mos.)', 'enrollment_duration']),
            'Enrollment_Close_Date': self._get_field(t, ['Enrollment_Close_Date', 'Enrollment Close Date']),
            'Treatment_Duration_Mos': self._get_field(t, ['Treatment_Duration_Mos', 'Treatment Duration (Mos.)', 'treatment_duration']),
            'Primary_Completion_Date': self._get_field(t, ['Primary_Completion_Date', 'Primary Completion Date', 'primary_completion_date']),
            'Full_Completion_Date': self._get_field(t, ['Full_Completion_Date', 'Full Completion Date', 'completion_date']),
            
            # Patient population
            'Patient_Population': self._get_field(t, ['Patient_Population', 'Patient Population', 'patient_population']),
            'Inclusion_Criteria': self._get_field(t, ['Inclusion_Criteria', 'Inclusion Criteria', 'inclusion_criteria', 'eligibility_criteria']),
            'Exclusion_Criteria': self._get_field(t, ['Exclusion_Criteria', 'Exclusion Criteria', 'exclusion_criteria']),
            'Patient_Gender': self._get_field(t, ['Patient_Gender', 'Patient Gender', 'gender', 'sex']),
            'Patient_Age_Group': self._get_field(t, ['Patient_Age_Group', 'Patient Age Group', 'age_group']),
            'Min_Patient_Age': self._get_field(t, ['Min_Patient_Age', 'Min Patient Age', 'minimum_age']),
            'Max_Patient_Age': self._get_field(t, ['Max_Patient_Age', 'Max Patient Age', 'maximum_age']),
            
            # Enrollment
            'Target_Accrual': self._get_field(t, ['Target_Accrual', 'Target Accrual', 'enrollment', 'enrollment_count']),
            'Actual_Accrual': self._get_field(t, ['Actual_Accrual', 'Actual Accrual (No. of patients)', 'actual_enrollment']),
            'Pts_Site_Mo': self._get_field(t, ['Pts_Site_Mo', 'Pts/Site/Mo', 'enrollment_rate']),
            
            # Sites and geography
            'Reported_Sites': self._get_field(t, ['Reported_Sites', 'Reported Sites', 'sites']),
            'Trial_Region': self._get_field(t, ['Trial_Region', 'Trial Region', 'region']),
            'Countries': self._get_field(t, ['Countries', 'countries']),
            'Countries_Count': self._get_field(t, ['Countries_Count', 'Countries Count']),
            
            # Treatment and study design
            'Prior_Concurrent_Therapy': self._get_field(t, ['Prior_Concurrent_Therapy', 'Prior/Concurrent Therapy']),
            'Treatment_Plan': self._get_field(t, ['Treatment_Plan', 'Treatment Plan', 'treatment_plan', 'intervention_description']),
            'Study_Design': self._get_field(t, ['Study_Design', 'Study Design', 'study_design', 'design']),
            'Study_Keywords': self._get_field(t, ['Study_Keywords', 'Study Keywords', 'keywords']),
            
            # Results and outcomes
            'Trial_Results': self._get_field(t, ['Trial_Results', 'Trial Results', 'results', 'results_summary']),
            'Trial_Outcomes': self._get_field(t, ['Trial_Outcomes', 'Trial Outcomes', 'outcomes']),
            'Outcome_Details': self._get_field(t, ['Outcome_Details', 'Outcome Details']),
            'Disposition_of_Patients': self._get_field(t, ['Disposition_of_Patients', 'Disposition of Patients']),
            
            # Additional metadata
            'Trial_Notes': self._get_field(t, ['Trial_Notes', 'Trial Notes', 'notes']),
            'Trial_Tag_Attribute': self._get_field(t, ['Trial_Tag_Attribute', 'Trial Tag/Attribute']),
            'Decentralized_DCT_Attributes': self._get_field(t, ['Decentralized_DCT_Attributes', 'Decentralized (DCT) Attributes']),
            'Associated_CRO': self._get_field(t, ['Associated_CRO', 'Associated CRO', 'cro']),
            'Record_URL': self._get_field(t, ['Record_URL', 'Record URL', 'url', 'study_url']),
        }
        
        return fields

    def _get_field(self, data: Dict, keys: List[str], default: str = '') -> str:
        """Helper to get field with multiple possible key names, including camelCase variants"""
        # Expand keys to include camelCase variants
        expanded_keys = []
        for key in keys:
            expanded_keys.append(key)
            # Add camelCase variants for snake_case keys
            if '_' in key or ' ' in key:
                variants = self._get_camelcase_mapping(key)
                expanded_keys.extend(variants)
        
        # Try all key variants
        for key in expanded_keys:
            if key in data and data[key] and str(data[key]).strip() and str(data[key]) != 'N/A':
                value = data[key]
                # Convert to string if not already
                if not isinstance(value, str):
                    value = str(value)
                return value.strip()
        return default
    
    def _get_camelcase_mapping(self, snake_case: str) -> List[str]:
        """
        Convert snake_case field name to possible camelCase variants
        e.g., Primary_Tested_Drug -> ['primaryTestedDrug', 'primaryDrug', 'Primary_Tested_Drug']
        """
        variants = [snake_case]  # Original
        
        # Remove spaces and convert to camelCase
        if ' ' in snake_case:
            variants.append(snake_case.replace(' ', ''))
        
        # Convert snake_case to camelCase
        parts = snake_case.split('_')
        if len(parts) > 1:
            camel = parts[0].lower() + ''.join(word.capitalize() for word in parts[1:])
            variants.append(camel)
            
            # Also try abbreviated versions
            if len(parts) >= 3:
                # e.g., Primary_Tested_Drug -> primaryDrug (last part)
                abbreviated = parts[0].lower() + parts[-1].capitalize()
                variants.append(abbreviated)
        
        # Try lowercase version
        variants.append(snake_case.lower().replace('_', ''))
        
        return variants

    def _format_trial_context(self, trials: List[Any], relevant_columns: List[str]) -> str:
        """Format comprehensive trial information for the prompt"""
        context = []
        trials_with_data = 0
        
        for idx, trial in enumerate(trials[:15]):  # Use up to 15 reference trials
            fields = self._extract_trialtrove_fields(trial)
            
            trial_id = fields.get('Trial_ID', f'Trial_{idx+1}')
            trial_info = [f"\n{'='*60}", f"REFERENCE TRIAL {idx+1}: {trial_id}", f"{'='*60}"]
            
            # Track if this trial has any meaningful data
            has_data = False
            
            # Add requested relevant columns first
            for col in relevant_columns:
                value = fields.get(col)
                if value and value != 'N/A' and str(value).strip():
                    has_data = True
                    # Truncate very long fields
                    if len(str(value)) > 500:
                        value = str(value)[:500] + "... [truncated]"
                    trial_info.append(f"\n{col}:\n{value}")
            
            # Also check for any other non-empty fields
            if not has_data:
                # Try to add ANY non-empty fields from the trial
                for key, value in fields.items():
                    if value and value != 'N/A' and str(value).strip():
                        has_data = True
                        if len(str(value)) > 300:
                            value = str(value)[:300] + "... [truncated]"
                        trial_info.append(f"\n{key}:\n{value}")
                        if len(trial_info) > 10:  # Limit to prevent too much data
                            break
            
            if has_data:
                trials_with_data += 1
                context.append('\n'.join(trial_info))
        
        print(f"📊 Formatted {trials_with_data}/{len(trials[:15])} trials with actual data")
        
        if trials_with_data == 0:
            print(f"⚠️ WARNING: No trial data found in any of the {len(trials[:15])} trials!")
            print(f"   First trial keys: {list(trials[0].keys()) if trials and isinstance(trials[0], dict) else 'Not a dict'}")
        
        return '\n\n'.join(context) if context else "No reference trial data available."

    def _create_prompt(self, section_type: str, trials: List[Any], 
                      authored_sections: Dict, reference_info: str) -> List[Dict]:
        """Create comprehensive prompt for section generation"""
        config = self.section_configs.get(section_type, {})
        if not config:
            # Fallback for unknown section types
            return self._create_generic_prompt(section_type, trials, reference_info)
        
        system_prompt = config.get('system_prompt', '')
        relevant_columns = config.get('relevant_columns', [])
        output_format = config.get('output_format', '')
        
        trial_context = self._format_trial_context(trials, relevant_columns)
        
        # Format already authored sections
        authored_context = ""
        if authored_sections:
            authored_context = "\n\n**Previously Generated Sections (use for consistency):**\n"
            for section_name, content in authored_sections.items():
                if content:
                    authored_context += f"\n--- {section_name} ---\n{content[:300]}...\n"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""
You are generating the {section_type.upper()} section for a new clinical trial protocol.

**REFERENCE TRIALS DATA:**
{trial_context}
{authored_context}

**TARGET STUDY INFORMATION:**
{reference_info if reference_info else "Use the reference trials as the primary basis for generation."}

**YOUR TASK:**
{output_format}

**CRITICAL REQUIREMENTS:**
1. Extract ONLY factual information from the reference trials provided
2. Use specific data points (numbers, timeframes, measurements) from reference trials
3. Cite specific trials by their ID when referencing data
4. Maintain scientific accuracy and medical terminology
5. Ensure consistency with any previously generated sections
6. Focus exclusively on the {section_type} section - do not include other content
7. Use professional, regulatory-appropriate language
8. Include relevant details that demonstrate depth of analysis

**OUTPUT:**
Generate ONLY the {section_type} content following the format specified above. Do not include section headers, explanations, or meta-commentary.
"""}
        ]
        
        return messages

    def _create_generic_prompt(self, section_type: str, trials: List[Any], reference_info: str) -> List[Dict]:
        """Fallback generic prompt for unknown section types"""
        trial_context = self._format_trial_context(trials, [
            'Trial_Title', 'Disease', 'Primary_Tested_Drug', 'Trial_Objective', 
            'Study_Design', 'Primary_Endpoint_Details'
        ])
        
        return [
            {"role": "system", "content": f"You are an expert in authoring {section_type} sections for clinical trial protocols."},
            {"role": "user", "content": f"""
Generate a comprehensive {section_type} section based on these reference trials:

{trial_context}

Additional context: {reference_info}

Provide a well-structured, detailed {section_type} section appropriate for a clinical trial protocol.
"""}
        ]

    async def _make_api_call(self, messages: List[Dict]) -> Optional[str]:
        """Make API call with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Extract system prompt and user prompt from messages
                system_prompt = None
                user_prompt = ""
                
                for msg in messages:
                    if msg.get("role") == "system":
                        system_prompt = msg.get("content")
                    elif msg.get("role") == "user":
                        user_prompt = msg.get("content")
                
                # Call llm_agent with correct signature
                response = await llm_agent.generate_response(
                    prompt=user_prompt,
                    system_prompt=system_prompt
                )
                return response
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"⚠️ API call failed (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    log_error(e, "Protocol generation API call")
                    raise
        return None

    async def generate_section(self, section_type: str, trials: List[Any], 
                              reference_info: str = "") -> str:
        """
        Generate a specific protocol section with comprehensive TrialTrove data extraction
        
        Args:
            section_type: Type of section to generate (e.g., 'introduction', 'rationale', 'objectives')
            trials: List of reference trials (ClinicalTrialResult objects or dicts)
            reference_info: Additional context about the target study
            
        Returns:
            Generated section content as string
        """
        if not trials:
            print(f"⚠️ No reference trials provided for {section_type}")
            return ""
        
        try:
            print(f"📝 Generating {section_type} section with {len(trials)} reference trials...")
            
            # Create prompt and make API call
            messages = self._create_prompt(section_type, trials, self.authored_sections, reference_info)
            response = await self._make_api_call(messages)
            
            if response:
                # Store the generated content for cross-reference
                section_key = section_type.replace('_', ' ').title()
                self.authored_sections[section_key] = response
                print(f"✅ Generated {section_type} section ({len(response)} characters)")
                return response
            else:
                print(f"❌ No response received for {section_type}")
                return ""
                
        except Exception as e:
            log_error(e, f"Protocol section generation: {section_type}")
            print(f"❌ Error generating {section_type}: {str(e)}")
            return ""

    async def generate_full_protocol(self, trials: List[Any], 
                                    reference_info: str = "") -> Dict[str, str]:
        """
        Generate a complete protocol with all sections
        
        Returns:
            Dictionary mapping section names to their content
        """
        print(f"🔬 Generating full protocol with {len(trials)} reference trials...")
        
        sections_to_generate = [
            'title',
            'introduction',
            'rationale',
            'background',
            'hypothesis',
            'primary_objectives',
            'secondary_objectives',
            'primary_endpoints',
            'secondary_endpoints',
            'inclusion_criteria',
            'exclusion_criteria',
            'study_design',
            'schedule_of_activities',
            'schema'
        ]
        
        results = {}
        
        for section_type in sections_to_generate:
            print(f"\n📝 Generating {section_type}...")
            content = await self.generate_section(section_type, trials, reference_info)
            results[section_type] = content
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(1)
        
        print(f"\n✅ Full protocol generation complete!")
        print(f"📊 Generated {len(results)} sections")
        print(f"📏 Total content length: {sum(len(v) for v in results.values())} characters")
        
        return results

    def get_section_preview(self, section_type: str) -> Dict[str, Any]:
        """Get information about a section's configuration"""
        config = self.section_configs.get(section_type, {})
        return {
            'section_type': section_type,
            'relevant_columns': config.get('relevant_columns', []),
            'has_custom_prompt': bool(config.get('system_prompt')),
            'has_format_spec': bool(config.get('output_format'))
        }

    def get_all_sections(self) -> List[str]:
        """Get list of all supported section types"""
        return list(self.section_configs.keys())

    async def generate_inclusion_criteria(self, trials: List[Any], 
                                        reference_info: str = "") -> str:
        """Generate inclusion criteria (alias for backward compatibility)"""
        return await self.generate_section('inclusion_criteria', trials, reference_info)

    async def generate_exclusion_criteria(self, trials: List[Any], 
                                         reference_info: str = "") -> str:
        """Generate exclusion criteria (alias for backward compatibility)"""
        return await self.generate_section('exclusion_criteria', trials, reference_info)


# Create singleton instance for backward compatibility
protocol_authoring_agent = ProtocolAuthoringAgent()
