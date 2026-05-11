"""
Protocol Authoring Agent for Clinical Research Assistant
Integrates patient profiler capabilities for generating clinical trial protocol components
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
    """Agent for generating clinical trial protocol components using patient profiler capabilities"""
    
    def __init__(self):
        self.client = llm_agent.client
        self.section_configs = {
            'introduction': {
                'system_prompt': "You are an expert in authoring introductions for clinical trials. Focus on creating clear and scientific introductions specific to the clinical trials. Include in-text citations and a reference section to relevant publications where applicable.",
                'relevant_columns': [
                    'Trial_ID', 'Trial_Title', 'Disease', 'Therapeutic_Area',
                    'Primary_Tested_Drug', 'Trial_Objective', 'Study_Design', 'Treatment_Plan'
                ],
                'output_format': """Write a single paragraph limited to 250 words. Start with the disease and drug background information,
then transition into why the trial is important based upon the objective."""
            },
            'rationale': {
                'system_prompt': "You are an expert in authoring rationales for clinical trials. Focus on creating clear and compelling rationales that justify the need for the trial.",
                'relevant_columns': [
                    'Trial_ID', 'Trial_Title', 'Disease', 'Primary_Tested_Drug',
                    'Trial_Objective', 'Study_Design', 'Treatment_Plan',
                    'Primary_Endpoint_Details', 'Secondary_Other_Endpoint_Details'
                ],
                'output_format': """Write 2-3 paragraphs that:
1. First paragraph: Explain the current treatment landscape and its limitations
2. Second paragraph: Present the scientific rationale for the new approach
3. Third paragraph (optional): Describe the potential impact and benefits

Keep the total length under 300 words."""
            },
            'background': {
                'system_prompt': "You are an expert in authoring background sections for clinical trials. Focus on creating comprehensive and scientifically accurate background information. Include in-text citations and a reference section to relevant publications where applicable.",
                'relevant_columns': [
                    'Trial_ID', 'Trial_Title', 'Disease', 'Primary_Tested_Drug',
                    'Primary_Tested_Drug_Mechanism_Of_Action', 'Other_Tested_Drug',
                    'Other_Tested_Drug_Mechanism_Of_Action', 'Patient_Population',
                    'Trial_Objective', 'Study_Design'
                ],
                'output_format': """Write 3-4 paragraphs that cover:
1. Disease background and epidemiology
2. Current treatment landscape and limitations
3. Investigational product(s) mechanism of action and development
4. Relevant clinical evidence and previous studies

Keep the total length under 400 words."""
            },
            'hypothesis': {
                'system_prompt': "You are an expert in authoring hypotheses for clinical trials. Focus on creating clear, testable, and scientifically sound hypotheses. Include in-text citations to relevant publications where applicable.",
                'relevant_columns': [
                    'Trial_ID', 'Trial_Title', 'Disease', 'Primary_Tested_Drug',
                    'Trial_Objective', 'Study_Design', 'Primary_Endpoint_Details',
                    'Secondary_Other_Endpoint_Details', 'Treatment_Plan'
                ],
                'output_format': """Write 2-3 hypotheses that:
1. Are numbered and clearly stated
2. Include specific outcomes and measurements
3. Reference the relevant endpoints
4. Are supported by the background and rationale

Example format:
1. [Drug X] will demonstrate superior efficacy compared to [standard of care] in improving [specific outcome] as measured by [endpoint] at [timepoint].
2. [Drug X] will show a favorable safety profile with [specific safety measure] comparable to [standard of care].

Keep the total length under 200 words."""
            },
            'primary_objectives': {
                'system_prompt': "You are an expert in authoring primary objectives for clinical trials. Focus on creating clear, specific, and measurable primary objectives that directly address the main study goals. Include in-text citations to trials and relevant publications with references where applicable.",
                'relevant_columns': [
                    'Trial_ID', 'Trial_Title', 'Disease', 'Primary_Tested_Drug',
                    'Trial_Objective', 'Study_Design', 'Primary_Endpoint_Details', 'Treatment_Plan'
                ],
                'output_format': """Write primary objectives in this format:

Primary Objectives:
1. [Primary objective 1]
2. [Primary objective 2]

Each objective should:
- Be specific and measurable
- Include the intervention and comparison
- Reference the relevant primary endpoints
- Include timepoints where applicable
- Focus on the main study goals
- Be limited to 2-3 key objectives
- Include in-text citations to specific trials that are relevant to the criteria, include multiple citations if relevant

Keep the total length under 200 words."""
            },
            'secondary_objectives': {
                'system_prompt': "You are an expert in authoring secondary objectives for clinical trials. Focus on creating clear, specific, and measurable secondary objectives that support the primary objectives. Include in-text citations to relevant publications and trials where applicable.",
                'relevant_columns': [
                    'Trial_ID', 'Trial_Title', 'Disease', 'Primary_Tested_Drug',
                    'Trial_Objective', 'Study_Design', 'Secondary_Other_Endpoint_Details', 'Treatment_Plan'
                ],
                'output_format': """Write secondary objectives in this format:

Secondary Objectives:
1. [Secondary objective 1]
2. [Secondary objective 2]
3. [Secondary objective 3]

Each objective should:
- Be specific and measurable
- Include the intervention and comparison
- Reference the relevant secondary endpoints
- Include timepoints where applicable
- Support and complement the primary objectives
- Focus on exploratory and supportive goals

Keep the total length under 200 words."""
            },
            'primary_endpoints': {
                'system_prompt': "You are an expert in authoring primary endpoints for clinical trials. Focus on creating clear, specific, and measurable primary endpoints that directly assess the main study outcomes. Include in-text citations to relevant publications and trials where applicable.",
                'relevant_columns': [
                    'Trial_ID', 'Trial_Title', 'Disease', 'Primary_Tested_Drug',
                    'Trial_Objective', 'Study_Design', 'Primary_Endpoint_Details',
                    'Treatment_Plan', 'Patient_Population'
                ],
                'output_format': """Write primary endpoints in this format:

Primary Endpoints:
1. [Primary endpoint 1]
   - Measurement: [How it will be measured]
   - Timepoint: [When it will be measured]
   - Analysis: [How it will be analyzed]

Each endpoint should:
- Be specific and measurable
- Include clear measurement methods
- Specify timepoints
- Include analysis methods
- Be aligned with primary objectives
- Focus on the main study outcomes

Keep the total length under 300 words."""
            },
            'secondary_endpoints': {
                'system_prompt': "You are an expert in authoring secondary endpoints for clinical trials. Focus on creating clear, specific, and measurable secondary endpoints that support the primary endpoints. Include in-text citations to relevant publications and trials where applicable. Include as many secondary endpoints as necessary.",
                'relevant_columns': [
                    'Trial_ID', 'Trial_Title', 'Disease', 'Primary_Tested_Drug',
                    'Trial_Objective', 'Study_Design', 'Secondary_Other_Endpoint_Details',
                    'Treatment_Plan', 'Patient_Population'
                ],
                'output_format': """Write secondary endpoints in this format:

Secondary Endpoints:
1. [Secondary endpoint 1]
   - Measurement: [How it will be measured]
   - Timepoint: [When it will be measured]
   - Analysis: [How it will be analyzed]

2. [Secondary endpoint 2]
   - Measurement: [How it will be measured]
   - Timepoint: [When it will be measured]
   - Analysis: [How it will be analyzed]

3. [Secondary endpoint 3]
   - Measurement: [How it will be measured]
   - Timepoint: [When it will be measured]
   - Analysis: [How it will be analyzed]

Each endpoint should:
- Be specific and measurable
- Include clear measurement methods
- Specify timepoints
- Include analysis methods
- Be aligned with secondary objectives
- Focus on supportive and exploratory outcomes

Keep the total length under 300 words."""
            }
        }
        
        # Store authored sections
        self.authored_sections = {
            'Introduction': '',
            'Rationale': '',
            'Background': '',
            'Hypothesis': '',
            'Inclusion Criteria': '',
            'Exclusion Criteria': '',
            'Primary Objectives': '',
            'Secondary Objectives': '',
            'Primary Endpoints': '',
            'Secondary Endpoints': ''
        }

    def _normalize_trial(self, trial: Any) -> Dict[str, Any]:
        """Normalize trial input (ClinicalTrialResult or dict) into a standard dict."""
        if hasattr(trial, 'dict'):
            t = trial.dict()
        elif isinstance(trial, dict):
            t = trial
        else:
            t = {}
        
        # Extract common fields with robust key mapping
        nct_id = (
            t.get('nct_id') or t.get('NCTId') or t.get('nctId') or t.get('Trial_ID') or t.get('TrialId') or t.get('trial_id')
        )
        title = (
            t.get('title') or t.get('Title') or t.get('Trial_Title') or t.get('trial_title') or t.get('brief_title')
        )
        condition = (
            t.get('condition') or t.get('Condition') or t.get('Disease') or t.get('disease')
        )
        intervention = (
            t.get('intervention') or t.get('Intervention') or t.get('Primary_Tested_Drug') or t.get('primary_tested_drug')
        )
        description = (
            t.get('description') or t.get('Description') or t.get('Trial_Objective') or t.get('trial_objective') or t.get('brief_description')
        )
        study_design = t.get('Study_Design') or t.get('study_design') or 'Clinical Trial'
        patient_population = t.get('Patient_Population') or t.get('patient_population') or condition
        moa_primary = t.get('Primary_Tested_Drug_Mechanism_Of_Action') or t.get('primary_tested_drug_mechanism_of_action')
        moe_other = t.get('Other_Tested_Drug_Mechanism_Of_Action') or t.get('other_tested_drug_mechanism_of_action')
        other_drug = t.get('Other_Tested_Drug') or t.get('other_tested_drug')
        primary_endpoint_details = t.get('Primary_Endpoint_Details') or t.get('primary_endpoint_details') or description
        secondary_endpoint_details = t.get('Secondary_Other_Endpoint_Details') or t.get('secondary_other_endpoint_details') or description
        
        # Enhanced field extraction for TrialTrove data
        phase = t.get('phase') or t.get('Phase')
        status = t.get('status') or t.get('Status')
        sponsor = t.get('sponsor') or t.get('Sponsor') or t.get('Sponsor_Collaborator')
        enrollment = t.get('enrollment') or t.get('Enrollment') or t.get('enrollment_count')
        start_date = t.get('start_date') or t.get('Start_Date') or t.get('study_start_date')
        
        # Extract inclusion/exclusion criteria if available
        inclusion_criteria = (
            t.get('inclusion_criteria') or t.get('Inclusion_Criteria') or t.get('InclusionCriteria') or
            (t.get('metadata', {}).get('trialtrove', {}).get('inclusion_criteria') if isinstance(t.get('metadata'), dict) else None)
        )
        exclusion_criteria = (
            t.get('exclusion_criteria') or t.get('Exclusion_Criteria') or t.get('ExclusionCriteria') or
            (t.get('metadata', {}).get('trialtrove', {}).get('exclusion_criteria') if isinstance(t.get('metadata'), dict) else None)
        )
        
        # Extract endpoints if available
        primary_endpoint = (
            t.get('primary_endpoint') or t.get('Primary_Endpoint') or t.get('Primary_Endpoint_Details') or
            (t.get('metadata', {}).get('trialtrove', {}).get('primary_endpoint') if isinstance(t.get('metadata'), dict) else None)
        )
        secondary_endpoint = (
            t.get('secondary_endpoint') or t.get('Secondary_Endpoint') or t.get('Secondary_Other_Endpoint_Details') or
            (t.get('metadata', {}).get('trialtrove', {}).get('secondary_endpoint') if isinstance(t.get('metadata'), dict) else None)
        )
        
        result = {
            'nct_id': nct_id,
            'title': title,
            'condition': condition,
            'intervention': intervention,
            'description': description,
            'Study_Design': study_design,
            'Patient_Population': patient_population,
            'Primary_Tested_Drug_Mechanism_Of_Action': moa_primary,
            'Other_Tested_Drug_Mechanism_Of_Action': moe_other,
            'Other_Tested_Drug': other_drug,
            'Primary_Endpoint_Details': primary_endpoint_details,
            'Secondary_Other_Endpoint_Details': secondary_endpoint_details,
            # Enhanced fields
            'phase': phase,
            'status': status,
            'sponsor': sponsor,
            'enrollment': enrollment,
            'start_date': start_date,
            'inclusion_criteria': inclusion_criteria,
            'exclusion_criteria': exclusion_criteria,
            'primary_endpoint': primary_endpoint,
            'secondary_endpoint': secondary_endpoint,
        }
        
        return result

    def _format_trial_context(self, trials: List[ClinicalTrialResult], relevant_columns: List[str]) -> str:
        """Format trial information for the prompt"""
        context = []
        
        for idx, t in enumerate(trials[:10]):  # Limit to 10 trials
            norm = self._normalize_trial(t)
            
            trial_id_label = norm.get('nct_id') or f"T{idx+1}"
            trial_info = [f"\nTrial ID: {trial_id_label}:"]
            
            # Map normalized fields to expected column names
            field_mapping = {
                'Trial_ID': norm.get('nct_id'),
                'Trial_Title': norm.get('title'),
                'Disease': norm.get('condition'),
                'Therapeutic_Area': norm.get('condition'),
                'Primary_Tested_Drug': norm.get('intervention'),
                'Trial_Objective': norm.get('description'),
                'Study_Design': norm.get('Study_Design') or 'Clinical Trial',
                'Treatment_Plan': norm.get('intervention'),
                'Primary_Endpoint_Details': norm.get('Primary_Endpoint_Details') or norm.get('description'),
                'Secondary_Other_Endpoint_Details': norm.get('Secondary_Other_Endpoint_Details') or norm.get('description'),
                'Patient_Population': norm.get('Patient_Population') or norm.get('condition'),
                'Primary_Tested_Drug_Mechanism_Of_Action': norm.get('Primary_Tested_Drug_Mechanism_Of_Action') or 'Not specified',
                'Other_Tested_Drug': norm.get('Other_Tested_Drug') or '',
                'Other_Tested_Drug_Mechanism_Of_Action': norm.get('Other_Tested_Drug_Mechanism_Of_Action') or '',
                # Enhanced TrialTrove field mappings
                'Inclusion_Criteria': norm.get('inclusion_criteria'),
                'Exclusion_Criteria': norm.get('exclusion_criteria'),
                'Primary_Endpoint': norm.get('primary_endpoint'),
                'Secondary_Endpoint': norm.get('secondary_endpoint'),
            }
            
            # Add enhanced TrialTrove fields to the mapping
            enhanced_mapping = {
                'Phase': norm.get('phase'),
                'Status': norm.get('status'),
                'Sponsor': norm.get('sponsor'),
                'Enrollment': norm.get('enrollment'),
                'Start_Date': norm.get('start_date'),
                'Inclusion_Criteria': norm.get('inclusion_criteria'),
                'Exclusion_Criteria': norm.get('exclusion_criteria'),
                'Primary_Endpoint': norm.get('primary_endpoint'),
                'Secondary_Endpoint': norm.get('secondary_endpoint'),
            }
            
            # Merge the mappings
            field_mapping.update(enhanced_mapping)
            
            # Process relevant columns first
            for col in relevant_columns:
                value = field_mapping.get(col, 'N/A')
                if value and value != 'N/A':
                    if isinstance(value, str) and len(value) > 200:
                        value = value[:200] + "..."
                    trial_info.append(f"{col}: {value}")
            
            # Add additional context fields that are commonly useful for protocol generation
            additional_fields = ['Phase', 'Status', 'Sponsor', 'Enrollment', 'Inclusion_Criteria', 'Exclusion_Criteria']
            for field in additional_fields:
                if field not in relevant_columns:  # Don't duplicate
                    value = field_mapping.get(field)
                    if value and value != 'N/A':
                        if isinstance(value, str) and len(value) > 200:
                            value = value[:200] + "..."
                        trial_info.append(f"{field}: {value}")
            
            context.append('\n'.join(trial_info))
        
        return '\n'.join(context)
    
    def _create_prompt(self, section_type: str, trials: List[ClinicalTrialResult], 
                      authored_sections: Dict, reference_info: str) -> List[Dict]:
        """Create the prompt for GPT model"""
        config = self.section_configs.get(section_type, {})
        system_prompt = config.get('system_prompt', '')
        relevant_columns = config.get('relevant_columns', [])
        output_format = config.get('output_format', '')
        
        trial_context = self._format_trial_context(trials, relevant_columns)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"""
As an expert clinician who is responsible for authoring clinical trial documents, generate {section_type} for a new trial following these strict requirements:

Input:
Reference trials: {trial_context}
Already generated content: {authored_sections}
Target study information: {reference_info}

Requirements:
1. Extract ONLY the key information required for the {section_type}
2. Use clear, standardized medical terminology
3. Use any sections already generated to inform your output
4. If target study information is provided, ensure the content is specifically tailored to that information
5. Maintain consistency with other generated sections
6. Focus on scientific accuracy and clinical relevance
7. Only include the {section_type}, do not include any other text

Output Format:
{output_format}
"""}
        ]
        
        return messages
    
    async def _make_api_call(self, messages: List[Dict]) -> Optional[str]:
        """Make API call with retry logic"""
        try:
            response = await llm_agent.generate_response(
                messages[1]["content"],  # Use the user message content
                system_prompt=messages[0]["content"]  # Use the system prompt
            )
            return response.strip()
        except Exception as e:
            print(f"API call failed: {str(e)}")
            raise
    
    async def generate_section(self, section_type: str, trials: List[ClinicalTrialResult], 
                              reference_info: str = "") -> str:
        """Generate a specific protocol section"""
        if not trials:
            return ""
        
        try:
            # Create prompt and make API call
            messages = self._create_prompt(section_type, trials, self.authored_sections, reference_info)
            response = await self._make_api_call(messages)
            
            # Store the generated content
            section_key = section_type.replace('_', ' ').title()
            self.authored_sections[section_key] = response
            
            return response
            
        except Exception as e:
            log_error(e, f"Protocol section generation: {section_type}")
            print(f"❌ Error generating {section_type}: {str(e)}")
            return ""
    
    async def generate_inclusion_criteria(self, trials: List[ClinicalTrialResult], 
                                        reference_info: str = "") -> str:
        """Generate inclusion criteria using the provided trials"""
        try:
            # Create specialized prompt for inclusion criteria with comprehensive trial context
            trial_context = self._format_trial_context(trials, [
                'Trial_ID', 'Trial_Title', 'Disease', 'Phase', 'Status', 'Sponsor', 
                'Enrollment', 'Inclusion_Criteria', 'Exclusion_Criteria', 'Primary_Endpoint', 'Secondary_Endpoint'
            ])
            
            prompt = f"""
As an expert clinician who is responsible for authoring clinical trial documents, generate a precise list of inclusion criteria following these strict requirements:

Input:
Reference trials: {trial_context}
Already generated content: {self.authored_sections}
Target study information: {reference_info}

Requirements:
1. Extract ONLY the most frequently occurring criteria across reference trials
2. Include exactly one criterion per clinical topic (no duplicates)
3. Each criterion must be directly connected to one or more endpoints, if they have already been generated
4. Maintain the same order as seen in reference trials
5. Use clear, standardized medical terminology
6. Keep criteria specific, including durations, scores, and tests
7. Use specific numeric values, units, and measurements
8. Include in-text citations to specific trials that are relevant to the criteria, include multiple citations if relevant
9. If target study information is provided, ensure the criteria are specifically tailored to that information
10. Use the detailed trial information provided above to extract specific inclusion criteria patterns

Output Format:
- Use EXACTLY this format for each line:
N. [Single Criterion] (Trial_ID1, Trial_ID2)

Example Format:
1. Age ≥ 18 years (365414)
2. Diagnosis of moderate-to-severe AD for at least 1 year (343960)

DO NOT:
- Add explanatory text
- Include rare/unique criteria
- Combine multiple conditions in one criterion
- Add notes or comments

Output only the numbered criteria list with trial IDs.
"""
            
            response = await llm_agent.generate_response(prompt)
            self.authored_sections['Inclusion Criteria'] = response
            return response
            
        except Exception as e:
            log_error(e, "Inclusion criteria generation")
            print(f"❌ Error generating inclusion criteria: {str(e)}")
            return ""
    
    async def generate_exclusion_criteria(self, trials: List[ClinicalTrialResult], 
                                        reference_info: str = "") -> str:
        """Generate exclusion criteria using the provided trials"""
        try:
            # Create specialized prompt for exclusion criteria with comprehensive trial context
            trial_context = self._format_trial_context(trials, [
                'Trial_ID', 'Trial_Title', 'Disease', 'Phase', 'Status', 'Sponsor', 
                'Enrollment', 'Inclusion_Criteria', 'Exclusion_Criteria', 'Primary_Endpoint', 'Secondary_Endpoint'
            ])
            
            prompt = f"""
As an expert clinician who is responsible for authoring clinical trial documents, generate a precise list of exclusion criteria following these strict requirements:

Input:
Reference trials: {trial_context}
Already generated content: {self.authored_sections}
Target study information: {reference_info}

Requirements:
1. Extract ONLY the most frequently occurring criteria across reference trials
2. Include exactly one criterion per clinical topic (no duplicates)
3. Each criterion must be directly connected to one or more endpoints, if they have already been generated
4. Maintain the same order as seen in reference trials
5. Use clear, standardized medical terminology
6. Keep criteria specific, including durations, scores, and tests
7. Use specific numeric values, units, and measurements
8. Include in-text citations to specific trials that are relevant to the criteria, include multiple citations if relevant
9. If target study information is provided, ensure the criteria are specifically tailored to that information
10. Use the detailed trial information provided above to extract specific exclusion criteria patterns

Output Format:
- Use EXACTLY this format for each line:
N. [Single Criterion] (Trial_ID1, Trial_ID2)

Example Format:
1. Age < 18 years (365414)
2. Known hypersensitivity to study drug (343960)

DO NOT:
- Add explanatory text
- Include rare/unique criteria
- Combine multiple conditions in one criterion
- Add notes or comments

Output only the numbered criteria list with trial IDs.
"""
            
            response = await llm_agent.generate_response(prompt)
            self.authored_sections['Exclusion Criteria'] = response
            return response
            
        except Exception as e:
            log_error(e, "Exclusion criteria generation")
            print(f"❌ Error generating exclusion criteria: {str(e)}")
            return ""
    
    async def edit_section(self, section_type: str, current_content: str, edit_instructions: str,
                           trials: List[ClinicalTrialResult], reference_info: str = "") -> str:
        """Apply edit instructions to an existing section, preserving structure/numbering/markdown."""
        try:
            section_key = section_type.replace('_', ' ').title()
            # Use enhanced trial context for editing
            trial_context = self._format_trial_context(trials, [
                'Trial_ID', 'Trial_Title', 'Disease', 'Phase', 'Status', 'Sponsor', 
                'Enrollment', 'Inclusion_Criteria', 'Exclusion_Criteria', 'Primary_Endpoint', 'Secondary_Endpoint'
            ]) if trials else ""
            system_prompt = "You are an expert protocol editor. Edit text precisely while preserving structure and numbering."
            user_prompt = (
                f"You will edit an existing clinical trial protocol section. Apply ONLY the requested changes.\n\n"
                f"SECTION: {section_key}\n\n"
                f"CURRENT CONTENT:\n\n{current_content}\n\n"
                f"EDIT INSTRUCTIONS:\n{edit_instructions}\n\n"
                f"CONTEXT:\nReference trials:\n{trial_context}\n\n"
                f"Target study information: {reference_info}\n\n"
                "STRICT REQUIREMENTS:\n"
                "1. Preserve markdown formatting and ordered list numbering (1., 2., ...).\n"
                "2. Do not remove existing content unless explicitly instructed.\n"
                "3. Integrate changes succinctly and correctly.\n"
                "4. If criteria/endpoints are lists, maintain one item per line; keep numbering consecutive.\n"
                "5. Do not add editor notes or commentary; output only the revised section content.\n"
            )
            response = await llm_agent.generate_response(user_prompt, system_prompt=system_prompt)
            revised = response.strip()
            # Update in-memory authored sections store
            self.authored_sections[section_key] = revised
            return revised
        except Exception as e:
            log_error(e, f"Protocol section edit: {section_type}")
            print(f"❌ Error editing {section_type}: {str(e)}")
            return current_content
    
    def get_authored_sections(self) -> Dict[str, str]:
        """Get all authored sections"""
        return self.authored_sections.copy()
    
    def clear_authored_sections(self) -> None:
        """Clear all authored sections"""
        for key in self.authored_sections:
            self.authored_sections[key] = ""
    
    def debug_trial_data(self, trials: List[Any]) -> str:
        """Debug method to inspect trial data structure"""
        debug_info = []
        debug_info.append(f"Total trials: {len(trials)}")
        
        for i, trial in enumerate(trials[:3]):  # Show first 3 trials
            debug_info.append(f"\nTrial {i+1}:")
            if hasattr(trial, '__dict__'):
                debug_info.append(f"  Type: {type(trial).__name__}")
                debug_info.append(f"  Attributes: {list(trial.__dict__.keys())}")
                # Show key fields
                for key in ['nct_id', 'title', 'condition', 'description', 'phase', 'status']:
                    if hasattr(trial, key):
                        value = getattr(trial, key)
                        if value:
                            debug_info.append(f"  {key}: {str(value)[:100]}...")
                # Show metadata if available
                if hasattr(trial, 'metadata') and trial.metadata:
                    debug_info.append(f"  Metadata keys: {list(trial.metadata.keys())}")
                    if 'trialtrove' in trial.metadata:
                        trialtrove_data = trial.metadata['trialtrove']
                        debug_info.append(f"  TrialTrove data keys: {list(trialtrove_data.keys())}")
                        # Show key TrialTrove fields
                        for key in ['inclusion_criteria', 'exclusion_criteria', 'primary_endpoint', 'secondary_endpoint']:
                            if key in trialtrove_data and trialtrove_data[key]:
                                value = trialtrove_data[key]
                                debug_info.append(f"    {key}: {str(value)[:100]}...")
            elif isinstance(trial, dict):
                debug_info.append(f"  Type: dict")
                debug_info.append(f"  Keys: {list(trial.keys())}")
                # Show key fields
                for key in ['nct_id', 'title', 'condition', 'description', 'phase', 'status']:
                    if key in trial and trial[key]:
                        value = trial[key]
                        debug_info.append(f"  {key}: {str(value)[:100]}...")
                # Show metadata if available
                if 'metadata' in trial and trial['metadata']:
                    debug_info.append(f"  Metadata keys: {list(trial['metadata'].keys())}")
                    if 'trialtrove' in trial['metadata']:
                        trialtrove_data = trial['metadata']['trialtrove']
                        debug_info.append(f"  TrialTrove data keys: {list(trialtrove_data.keys())}")
                        # Show key TrialTrove fields
                        for key in ['inclusion_criteria', 'exclusion_criteria', 'primary_endpoint', 'secondary_endpoint']:
                            if key in trialtrove_data and trialtrove_data[key]:
                                value = trialtrove_data[key]
                                debug_info.append(f"    {key}: {str(value)[:100]}...")
            else:
                debug_info.append(f"  Type: {type(trial)}")
                debug_info.append(f"  Value: {str(trial)[:100]}...")
        
        return '\n'.join(debug_info)
    
    async def generate_full_protocol(self, trials: List[ClinicalTrialResult], 
                                   reference_info: str = "", progress_callback=None) -> Dict[str, str]:
        """Generate a complete protocol with all sections"""
        try:
            print(f"🔧 Generating full protocol with {len(trials)} reference trials")
            
            # Generate all sections in logical order
            sections = [
                ('introduction', 'Introduction'),
                ('rationale', 'Rationale'),
                ('background', 'Background'),
                ('hypothesis', 'Hypothesis'),
                ('primary_objectives', 'Primary Objectives'),
                ('secondary_objectives', 'Secondary Objectives'),
                ('primary_endpoints', 'Primary Endpoints'),
                ('secondary_endpoints', 'Secondary Endpoints')
            ]
            
            results = {}
            
            for i, (section_type, section_name) in enumerate(sections):
                print(f"📝 Generating {section_name}...")
                
                # Progress updates are handled by the dynamic engine wrapper
                print(f"📝 Generating {section_name}...")
                
                content = await self.generate_section(section_type, trials, reference_info)
                results[section_name] = content
                
                # Progress completion is handled by the dynamic engine wrapper
                print(f"✅ Generated {section_name}")
            
            # Generate inclusion and exclusion criteria
            print("📝 Generating Inclusion Criteria...")
            
            inclusion_criteria = await self.generate_inclusion_criteria(trials, reference_info)
            results['Inclusion Criteria'] = inclusion_criteria
            
            print("✅ Generated Inclusion Criteria")
            
            print("📝 Generating Exclusion Criteria...")
            
            exclusion_criteria = await self.generate_exclusion_criteria(trials, reference_info)
            results['Exclusion Criteria'] = exclusion_criteria
            
            print("✅ Generated Exclusion Criteria")
            
            print("✅ Full protocol generation completed")
            return results
            
        except Exception as e:
            log_error(e, "Full protocol generation")
            print(f"❌ Error generating full protocol: {str(e)}")
            return {}

# Global protocol authoring agent instance
protocol_authoring_agent = ProtocolAuthoringAgent() 