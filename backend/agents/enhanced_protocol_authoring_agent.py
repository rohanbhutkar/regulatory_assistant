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

class EnhancedProtocolAuthoringAgent:
    """Enhanced agent for generating clinical trial protocol components with full TrialTrove integration"""
    
    def __init__(self):
        self.client = llm_agent.client
        
        # Comprehensive mapping of TrialTrove columns to use in each section
        self.section_configs = {
            'title': {
                'system_prompt': """You are an expert in creating protocol titles for clinical trials. 
Your titles must be complete, descriptive, and follow ICH GCP guidelines. They should clearly indicate:
- Study phase
- Design (randomized, double-blind, placebo-controlled, etc.)
- Study population
- Intervention(s) being tested
- Primary objective or indication""",
                'relevant_columns': [
                    'Trial_Title', 'Trial_Phase', 'Study_Design', 'Disease', 'Patient_Population',
                    'Primary_Tested_Drug', 'Other_Tested_Drug', 'Trial_Objective', 'Primary_Endpoint'
                ],
                'output_format': """Generate TWO titles:

FULL TITLE:
A [Phase X], [Design elements], Study to Evaluate [Primary objective] of [Intervention] in Patients with [Condition]

SHORT TITLE:
[Phase X] [Simplified condition] [Trial type] (e.g., "Phase 3 NSCLC RCT")

Requirements:
- Full title must be 150-200 characters
- Short title must be 30-50 characters
- Use standard abbreviations where appropriate
- Include all key study design elements in full title"""
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
Objectives must be precise, measurable, and aligned with regulatory requirements.""",
                'relevant_columns': [
                    'Trial_Objective', 'Primary_Endpoint', 'Primary_Endpoint_Group', 'Primary_Endpoint_Details',
                    'Study_Design', 'Treatment_Plan', 'Disease', 'Patient_Population', 'Primary_Tested_Drug'
                ],
                'output_format': """Write primary objectives (typically 1-2):

**Primary Objective(s):**

1. To evaluate the efficacy of [intervention] compared to [control] as measured by [primary endpoint] in [population] over [timeframe].

For each objective:
- State the intervention being tested
- Specify the comparison (if applicable)
- Name the exact primary endpoint
- Define the patient population precisely
- Include timepoint for assessment
- Specify type of analysis (superiority, non-inferiority, etc.)

Link objectives to specific endpoints from reference trials.
Maximum 200 words total."""
            },
            
            'secondary_objectives': {
                'system_prompt': """You are an expert in defining secondary objectives for clinical trials.
Secondary objectives support primary objectives and explore additional research questions.""",
                'relevant_columns': [
                    'Secondary_Other_Endpoint', 'Secondary_Other_Endpoint_Group', 'Secondary_Other_Endpoint_Details',
                    'Study_Design', 'Treatment_Plan', 'Disease', 'Patient_Population', 'Trial_Objective'
                ],
                'output_format': """Write 3-6 secondary objectives:

**Secondary Objectives:**

1. To assess [secondary outcome 1]...
2. To evaluate [secondary outcome 2]...
3. To characterize [safety/tolerability]...
4. To explore [exploratory endpoint]...

For each objective:
- Must support or complement primary objective
- Specify endpoint and measurement
- Include relevant subgroup analyses
- Address safety, tolerability, QoL, or exploratory endpoints
- Include timepoints

Reference similar secondary endpoints from reference trials.
Maximum 300 words total."""
            },
            
            'primary_endpoints': {
                'system_prompt': """You are an expert in defining clinical trial endpoints.
Primary endpoints must be clearly defined, validated, and clinically meaningful.""",
                'relevant_columns': [
                    'Primary_Endpoint', 'Primary_Endpoint_Group', 'Primary_Endpoint_Details',
                    'Study_Design', 'Treatment_Duration_Mos', 'Patient_Population', 'Disease'
                ],
                'output_format': """Define primary endpoint(s) with complete specifications:

**Primary Endpoint:**

**Endpoint:** [Name of endpoint]

**Definition:** [Precise definition of what is measured]

**Measurement Method:** 
- Instrument/scale/test used
- Validation status
- Sensitivity and specificity (if applicable)

**Timepoint(s):** 
- When measured (Week X, Month Y, etc.)
- Multiple assessments if applicable
- Primary analysis timepoint

**Analysis:**
- Statistical method
- Handling of missing data
- Sensitivity analyses planned

**Justification:**
- Why this endpoint was chosen
- Clinical meaningfulness
- Regulatory precedent
- Use in reference trials with outcomes

Include specific timepoints and measurement details from reference trials.
Maximum 400 words."""
            },
            
            'secondary_endpoints': {
                'system_prompt': """You are an expert in defining secondary and exploratory endpoints for trials.
Include comprehensive endpoint definitions covering efficacy, safety, and quality of life.""",
                'relevant_columns': [
                    'Secondary_Other_Endpoint', 'Secondary_Other_Endpoint_Group', 'Secondary_Other_Endpoint_Details',
                    'Study_Design', 'Treatment_Duration_Mos', 'Patient_Population', 'Disease',
                    'Oncology_Biomarker'
                ],
                'output_format': """Define 5-10 secondary endpoints comprehensively:

**Secondary Endpoints:**

1. **[Endpoint Name 1]**
   - **Definition:** [What is measured]
   - **Measurement:** [How and when]
   - **Analysis:** [Statistical approach]

2. **[Endpoint Name 2]**
   - **Definition:**...
   - **Measurement:**...
   - **Analysis:**...

Categories to cover:
- Additional efficacy endpoints
- Safety endpoints (AEs, SAEs, discontinuations)
- Quality of life measures
- Biomarker assessments
- Pharmacokinetic endpoints
- Time-to-event endpoints
- Subgroup analyses

Reference similar endpoints from reference trials with their measurement schedules.
Maximum 600 words."""
            },
            
            'inclusion_criteria': {
                'system_prompt': """You are an expert in writing inclusion criteria for clinical trials.
Criteria must be specific, measurable, and align with the target population.""",
                'relevant_columns': [
                    'Inclusion_Criteria', 'Patient_Population', 'Patient_Segment', 'Patient_Gender',
                    'Patient_Age_Group', 'Min_Patient_Age', 'Max_Patient_Age', 'Disease',
                    'Oncology_Biomarker', 'Prior_Concurrent_Therapy', 'Study_Design'
                ],
                'output_format': """Generate 8-15 inclusion criteria:

**Key Inclusion Criteria:**

1. **Demographics:**
   - Age: [range] years
   - Gender: [requirements]

2. **Diagnosis:**
   - Confirmed diagnosis of [condition]
   - Disease stage/classification
   - Biomarker status (if applicable)

3. **Disease Characteristics:**
   - Measurable disease (if applicable)
   - Performance status (ECOG, Karnofsky)
   - Disease-specific requirements

4. **Prior Therapy:**
   - Prior treatment requirements
   - Washout periods
   - Lines of therapy

5. **Laboratory Values:**
   - Organ function requirements
   - Hematology parameters
   - Chemistry parameters

6. **Other:**
   - Consent and compliance
   - Contraceptive requirements
   - Life expectancy

Use specific values and thresholds from reference trials. Each criterion must be unambiguous.
Maximum 500 words."""
            },
            
            'exclusion_criteria': {
                'system_prompt': """You are an expert in writing exclusion criteria for clinical trials.
Exclusion criteria protect patient safety and ensure data integrity.""",
                'relevant_columns': [
                    'Exclusion_Criteria', 'Patient_Population', 'Disease', 'Prior_Concurrent_Therapy',
                    'Oncology_Biomarker', 'Study_Design', 'Primary_Tested_Drug'
                ],
                'output_format': """Generate 10-20 exclusion criteria:

**Key Exclusion Criteria:**

1. **Medical History:**
   - Prior/concurrent malignancies
   - Significant medical conditions
   - Contraindications to study drug

2. **Prior Therapy:**
   - Prohibited prior treatments
   - Recent investigational agents
   - Timing restrictions

3. **Laboratory Abnormalities:**
   - Organ dysfunction
   - Laboratory value thresholds
   - Abnormal tests

4. **Concomitant Conditions:**
   - Active infections
   - Cardiac conditions
   - Neurologic conditions

5. **Pregnancy and Reproductive:**
   - Pregnancy/nursing
   - Reproductive restrictions

6. **Drug-Specific:**
   - Known hypersensitivity
   - Drug interactions
   - Pharmacogenomic exclusions

7. **Compliance:**
   - Inability to comply
   - Language/cognitive barriers

Use specific criteria from reference trials. Be comprehensive for safety.
Maximum 600 words."""
            },
            
            'study_design': {
                'system_prompt': """You are an expert in describing clinical trial designs.
Provide a complete overview of the study methodology.""",
                'relevant_columns': [
                    'Study_Design', 'Trial_Phase', 'Treatment_Plan', 'Enrollment_Duration_Mos',
                    'Treatment_Duration_Mos', 'Target_Accrual', 'Study_Keywords', 'Trial_Region'
                ],
                'output_format': """Write a comprehensive study design description (500-700 words):

**Overall Design:**
- Phase of study
- Design type (parallel, crossover, factorial, etc.)
- Randomization (if applicable)
- Blinding strategy
- Control/comparator

**Study Schema:**
- Screening period
- Treatment period(s)
- Follow-up period
- Total study duration

**Treatment Arms:**
For each arm:
- Treatment description
- Dosing regimen
- Duration
- Modifications allowed

**Randomization and Blinding:**
- Randomization ratio
- Stratification factors
- Blinding procedures
- Unblinding criteria

**Sample Size:**
- Target enrollment
- Justification
- Expected dropout
- Sites and regions

**Study Procedures:**
- Visit schedule overview
- Key assessments
- Safety monitoring

Reference similar designs from reference trials with their enrollment characteristics."""
            },
            
            'schedule_of_activities': {
                'system_prompt': """You are an expert in creating Schedule of Activities (SoA) for clinical trials.
The SoA must comprehensively list all study procedures and their timing.""",
                'relevant_columns': [
                    'Study_Design', 'Treatment_Duration_Mos', 'Primary_Endpoint_Details',
                    'Secondary_Other_Endpoint_Details', 'Treatment_Plan', 'Enrollment_Duration_Mos'
                ],
                'output_format': """Generate a detailed Schedule of Activities in table format:

Create a comprehensive table with:

**Columns:**
- Procedure/Assessment
- Screening
- Baseline/Day 1
- Week 2
- Week 4
- Week 8
- Week 12
- [Additional timepoints based on treatment duration]
- End of Treatment
- Safety Follow-up

**Rows (Categories):**

1. **Administrative:**
   - Informed consent
   - Inclusion/exclusion criteria
   - Demographics
   - Medical history
   - Concomitant medications

2. **Disease Assessments:**
   - Tumor imaging (if oncology)
   - Disease-specific assessments
   - Performance status

3. **Safety Assessments:**
   - Physical examination
   - Vital signs
   - ECG
   - Laboratory tests (hematology, chemistry, coagulation)
   - Adverse event assessment

4. **Efficacy Assessments:**
   - Primary endpoint measurements
   - Secondary endpoint measurements
   - QoL questionnaires

5. **PK/Biomarker:**
   - Blood samples
   - Tissue samples
   - Biomarker analyses

6. **Study Drug:**
   - Drug dispensing
   - Accountability
   - Compliance assessment

Include visit windows and specific timing from reference trials.
Present as a detailed narrative description of the table."""
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
        """Helper to get field with multiple possible key names"""
        for key in keys:
            if key in data and data[key]:
                value = data[key]
                # Convert to string if not already
                if not isinstance(value, str):
                    value = str(value)
                return value.strip() if value else default
        return default

    def _format_trial_context(self, trials: List[Any], relevant_columns: List[str]) -> str:
        """Format comprehensive trial information for the prompt"""
        context = []
        
        for idx, trial in enumerate(trials[:15]):  # Use up to 15 reference trials
            fields = self._extract_trialtrove_fields(trial)
            
            trial_id = fields.get('Trial_ID', f'Trial_{idx+1}')
            trial_info = [f"\n{'='*60}", f"REFERENCE TRIAL {idx+1}: {trial_id}", f"{'='*60}"]
            
            # Add requested relevant columns first
            for col in relevant_columns:
                value = fields.get(col)
                if value and value != 'N/A':
                    # Truncate very long fields
                    if len(value) > 500:
                        value = value[:500] + "... [truncated]"
                    trial_info.append(f"\n{col}:\n{value}")
            
            context.append('\n'.join(trial_info))
        
        return '\n\n'.join(context)

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
                response = await llm_agent.generate_response(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=2000
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








