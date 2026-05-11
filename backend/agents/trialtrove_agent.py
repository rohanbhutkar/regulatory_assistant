"""
TrialTrove Agent for Clinical Trial Data (2021 onwards)
Provides access to specialized trial data including biomarkers, protocol extracts, patient segments, and enrollment timelines
"""
import asyncio
import pandas as pd
import re
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from models.schemas import ClinicalTrialResult
from config import settings
from utils.logger import log_error
from utils.cache import cache_manager
from agents.llm_agent import llm_agent
from utils.regulatory_data_io import read_regulatory_csv

class TrialTroveAgent:
    """Agent for accessing TrialTrove clinical trial data (2021 onwards)"""
    
    def __init__(self):
        self.csv_file = "combined_trial_trove.csv"
        self.data = None
        self.loaded = False
        self.min_year = 2020  # Only data from 2021 onwards
        
    async def _load_data(self):
        """Load and filter the CSV data (2021 onwards only)"""
        if self.loaded:
            return
            
        try:
            print(f"📊 Loading TrialTrove data from {self.csv_file}")
            
            # Load CSV data
            df = read_regulatory_csv(self.csv_file, low_memory=False)
            
            # Filter for 2021 onwards based on Start Date
            df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
            df = df[df['Start Date'].dt.year >= self.min_year]
            
            # Clean and prepare data
            df = df.fillna('')
            
            # Process metadata for better search
            self._process_metadata(df)
            
            # Convert to list of dictionaries for easier processing
            self.data = df.to_dict('records')
            self.loaded = True
            
            print(f"✅ Loaded {len(self.data)} trials from 2021 onwards")
            
        except Exception as e:
            log_error(e, "TrialTrove data loading")
            print(f"❌ Error loading TrialTrove data: {e}")
            self.data = []
    
    def _process_metadata(self, df: pd.DataFrame):
        """Process metadata about the dataset for better search capabilities"""
        try:
            print("📊 Processing metadata for enhanced search...")
            
            # Get unique values for key searchable columns
            key_columns = [
                'Disease', 'Therapeutic Area', 'Trial Phase', 'Trial Status',
                'Patient Segment', 'Oncology Biomarker', 'Countries',
                'Sponsor/Collaborator', 'Primary Tested Drug'
            ]
            
            self.column_metadata = {}
            for col in key_columns:
                if col in df.columns:
                    # Get unique values and their counts
                    value_counts = df[col].value_counts()
                    
                    # Take top 100 most frequent values to avoid token limits
                    top_values = value_counts.head(100).index.tolist()
                    
                    self.column_metadata[col] = {
                        'unique_count': len(value_counts),
                        'top_values': top_values,
                        'sample_values': df[col].dropna().head(10).tolist()
                    }
            
            print(f"✅ Processed metadata for {len(self.column_metadata)} columns")
            
        except Exception as e:
            print(f"⚠️ Error processing metadata: {e}")
            self.column_metadata = {}
    
    async def search_studies(self, query: str, max_results: int = 50) -> List[ClinicalTrialResult]:
        """Search for clinical trials in TrialTrove data"""
        await self._load_data()
        
        if not self.data:
            return []
        
        # Create cache key
        cache_key = cache_manager.get_api_cache_key("trialtrove", "studies", {"query": query, "max_results": max_results})
        
        # Check cache first
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        print(f"🔍 TrialTroveAgent.search_studies called with query: '{query}', max_results: {max_results}")
        
        try:
            # Use LLM to generate search criteria
            search_criteria = await self._generate_search_criteria(query)
            
            # Filter data based on search criteria
            filtered_data = await self._filter_data_by_criteria(self.data, search_criteria)

            # Progressive fallback if too strict criteria yields zero
            if not filtered_data:
                print("   No results with initial criteria. Applying fallback relaxation...")

                # 1) Remove NOT_EMPTY-style filters first
                relaxed_criteria = dict(search_criteria)
                relaxed_filters = {k: v for k, v in relaxed_criteria.get("filters", {}).items() if v not in ("NOT_EMPTY", "HAS_BIOMARKER")}
                relaxed_criteria["filters"] = relaxed_filters
                print(f"   Fallback 1 - removed NOT_EMPTY/HAS_BIOMARKER filters: {relaxed_filters}")
                filtered_data = await self._filter_data_by_criteria(self.data, relaxed_criteria)

            if not filtered_data:
                # 2) Keep Phase filter, drop Therapeutic Area (some rows are subtype like 'Oncology: Colorectal')
                relaxed_criteria2 = dict(relaxed_criteria if 'relaxed_criteria' in locals() else search_criteria)
                rf2 = {}
                for k, v in relaxed_criteria2.get("filters", {}).items():
                    if k.lower() == "trial phase":
                        rf2[k] = v
                relaxed_criteria2["filters"] = rf2
                print(f"   Fallback 2 - kept only Phase filter: {rf2}")
                filtered_data = await self._filter_data_by_criteria(self.data, relaxed_criteria2)

            if not filtered_data:
                # 3) Drop all filters, rely on search terms
                relaxed_criteria3 = dict(search_criteria)
                relaxed_criteria3["filters"] = {}
                print("   Fallback 3 - dropped all filters, using search terms only")
                filtered_data = await self._filter_data_by_criteria(self.data, relaxed_criteria3)
            
            # Convert to ClinicalTrialResult objects
            results = []
            for trial in filtered_data[:max_results]:
                try:
                    result = self._convert_to_clinical_trial_result(trial)
                    if result:
                        results.append(result)
                except Exception as e:
                    log_error(e, f"Converting trial {trial.get('Trial ID', 'unknown')}")
                    continue
            
            # Sort by relevance score
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            # Cache results
            cache_manager.set(cache_key, results)
            
            print(f"✅ Found {len(results)} trials in TrialTrove data")
            return results
            
        except Exception as e:
            log_error(e, "TrialTrove search")
            print(f"❌ TrialTrove search failed: {e}")
            return []
    
    async def _generate_search_criteria(self, query: str) -> Dict[str, Any]:
        """Use LLM to generate search criteria from user query with sample data"""
        
        # Get sample data from relevant columns
        sample_data = {}
        if hasattr(self, 'column_metadata') and self.column_metadata:
            for col in ['Disease', 'Therapeutic Area', 'Patient Segment', 'Oncology Biomarker']:
                if col in self.column_metadata:
                    sample_data[col] = self.column_metadata[col]['sample_values'][:10]  # First 10 samples
        
        # If no metadata available, get some sample data directly
        if not sample_data and self.data:
            sample_trials = self.data[:5]  # First 5 trials
            sample_data = {
                'Disease': [trial.get('Disease', '') for trial in sample_trials if trial.get('Disease')],
                'Therapeutic Area': [trial.get('Therapeutic Area', '') for trial in sample_trials if trial.get('Therapeutic Area')],
                'Patient Segment': [trial.get('Patient Segment', '') for trial in sample_trials if trial.get('Patient Segment')],
                'Oncology Biomarker': [trial.get('Oncology Biomarker', '') for trial in sample_trials if trial.get('Oncology Biomarker')]
            }
        
        prompt = f"""
You are an expert clinical research analyst. Analyze the following query and generate search criteria for TrialTrove data.

QUERY: {query}

TRIALTROVE DATA FIELDS:
- Trial Title: Study title
- Disease: Medical conditions studied
- Therapeutic Area: Broad therapeutic category
- Patient Segment: Specific patient population
- Oncology Biomarker: Biomarker information
- Inclusion Criteria: Patient inclusion criteria
- Primary Endpoint: Primary study endpoints
- Secondary/Other Endpoint: Secondary endpoints
- Countries: Trial locations
- Sponsor/Collaborator: Study sponsor
- Trial Phase: Study phase
- Trial Status: Current status

SAMPLE DATA FROM RELEVANT COLUMNS:
{json.dumps(sample_data, indent=2)}

INSTRUCTIONS:
1. Look at the sample data above to understand the actual format of the data
2. Generate search terms that will match the actual data format (e.g., if Disease column has "Oncology: Lung, Non-Small Cell", use terms like "Lung" or "Non-Small Cell")
3. Identify key search terms from the query that will work with the actual data
4. Determine which fields to search in based on the query content
5. Generate appropriate search criteria that will find relevant trials
6. ALWAYS prioritize industry, especially top 20 pharma sponsors

IMPORTANT: The search terms must match the actual format of the data shown in the samples above.

FILTER VALUES:
- Use "NOT_EMPTY" to filter for fields that have any value
- Use "HAS_BIOMARKER" to filter for fields containing biomarker information
- Use specific values like "Oncology" for exact matches
- Do NOT use "!=" or other operators - use descriptive values instead

Return ONLY valid JSON with search criteria:

{{
    "search_fields": ["field1", "field2"],
    "search_terms": ["term1", "term2"],
    "filters": {{
        "field": "value",
        "field2": "NOT_EMPTY"
    }},
    "search_type": "exact|partial|fuzzy"
}}
"""
        
        try:
            response = await llm_agent.generate_structured_response(
                prompt,
                system_prompt="You are an expert clinical research analyst. Generate precise search criteria for trial data."
            )
            
            # Check for empty or error responses
            if not response or response.strip() == "":
                print(f"❌ LLM returned empty response for search criteria")
                raise ValueError("Empty LLM response")
            
            if response.startswith("Error generating structured response:"):
                print(f"❌ LLM returned error response: {response}")
                raise ValueError(f"LLM error: {response}")
            
            # Parse response - handle markdown code blocks and extract JSON
            cleaned_response = response
            
            # First, try to extract JSON from markdown code blocks
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                cleaned_response = json_match.group(1)
                print(f"   Extracted JSON from markdown code block")
            else:
                # Try to find JSON object in the response
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    cleaned_response = json_match.group(0)
                    print(f"   Extracted JSON object from response")
                else:
                    # Remove markdown code blocks if present
                    if response.strip().startswith('```'):
                        cleaned_response = re.sub(r'```json\s*', '', response)
                        cleaned_response = re.sub(r'```\s*$', '', cleaned_response)
                        cleaned_response = re.sub(r'```\s*', '', cleaned_response)
                        print(f"   Cleaned markdown formatting from response")
            
            try:
                criteria = json.loads(cleaned_response)
                print(f"   Successfully parsed LLM response")
                return criteria
            except json.JSONDecodeError as e:
                print(f"   JSON parsing failed: {e}")
                print(f"   Attempted to parse: {cleaned_response[:200]}...")
                raise
            
        except Exception as e:
            print(f"❌ Error generating search criteria: {e}")
            print(f"   Query: {query}")
            print(f"   Response was: {response if 'response' in locals() else 'No response'}")
            
            # Enhanced fallback to simple text search with better query parsing
            search_terms = []
            
            # Extract key terms from the query
            query_lower = query.lower()
            
            # Common medical terms to look for (expanded for better coverage)
            medical_terms = [
                "diabetes", "cancer", "lung", "breast", "prostate", "leukemia", "lymphoma",
                "cardiovascular", "hypertension", "asthma", "arthritis", "alzheimer",
                "parkinson", "multiple sclerosis", "hiv", "aids", "hepatitis", "kidney",
                "liver", "pancreatic", "ovarian", "cervical", "melanoma", "leukemia",
                "phase", "trial", "study", "clinical", "biomarker", "endpoint",
                "survival", "progression", "response", "safety", "efficacy",
                "oncology", "non-small", "small cell", "nsclc", "sclc", "metastatic",
                "advanced", "refractory", "relapsed", "first-line", "second-line"
            ]
            
            # Find medical terms in the query
            for term in medical_terms:
                if term in query_lower:
                    search_terms.append(term)
            
            # Extract specific disease terms that might be in the data format
            disease_patterns = [
                r"non-small cell lung cancer",
                r"nsclc",
                r"small cell lung cancer", 
                r"sclc",
                r"breast cancer",
                r"prostate cancer",
                r"colorectal cancer",
                r"pancreatic cancer",
                r"ovarian cancer",
                r"melanoma",
                r"leukemia",
                r"lymphoma"
            ]
            
            for pattern in disease_patterns:
                if re.search(pattern, query_lower):
                    # Extract the matched term and also individual words
                    match = re.search(pattern, query_lower)
                    if match:
                        full_term = match.group(0)
                        search_terms.append(full_term)
                        # Also add individual words
                        words = full_term.split()
                        search_terms.extend([w for w in words if len(w) > 2])
            
            # If no medical terms found, use the original query words
            if not search_terms:
                # Split query into words and filter out common words
                common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "can", "this", "that", "these", "those", "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them", "with", "trials", "clinical", "recent", "data", "information", "about", "find", "search", "look", "for"}
                words = [word.lower() for word in query.split() if word.lower() not in common_words and len(word) > 2]
                search_terms = words[:5]  # Take first 5 meaningful words
            
            # If still no terms, use the original query
            if not search_terms:
                search_terms = [query.lower()]
            
            # Remove duplicates while preserving order
            seen = set()
            unique_terms = []
            for term in search_terms:
                if term not in seen:
                    seen.add(term)
                    unique_terms.append(term)
            
            print(f"   Using fallback search terms: {unique_terms}")
            
            return {
                "search_fields": ["Trial Title", "Disease", "Therapeutic Area", "Patient Segment", "Oncology Biomarker"],
                "search_terms": unique_terms,
                "filters": {},
                "search_type": "partial"
            }
    
    async def _filter_data_by_criteria(self, data: List[Dict], criteria: Dict) -> List[Dict]:
        """Filter data based on search criteria using advanced filtering logic"""
        filtered_data = []
        
        search_fields = criteria.get("search_fields", ["Trial Title", "Disease"])
        search_terms = criteria.get("search_terms", [])
        filters = criteria.get("filters", {})
        search_type = criteria.get("search_type", "partial")
        
        # Combine all criteria into a single detailed message for WebSocket
        criteria_details = {
            "search_fields": search_fields,
            "search_terms": search_terms,
            "filters": filters,
            "search_type": search_type
        }
        criteria_summary = f"Search fields: {', '.join(search_fields)}; Search terms: {', '.join(search_terms) if search_terms else 'None'}; Filters: {filters if filters else 'None'}; Type: {search_type}"
        print(f"🔍 Filtering {len(data)} trials with criteria: {criteria_summary}")
        print(f"   Search fields: {search_fields}")
        print(f"   Search terms: {search_terms}")
        print(f"   Filters: {filters}")
        print(f"   Search type: {search_type}")
        
        # Debug: Show sample data for first few trials (only in verbose mode)
        if hasattr(self, 'verbose') and self.verbose:
            print(f"   Sample data (first 3 trials):")
            for i, trial in enumerate(data[:3]):
                print(f"     Trial {i+1}:")
                for field in search_fields:
                    if field in trial:
                        value = str(trial[field])[:50] + "..." if len(str(trial[field])) > 50 else str(trial[field])
                        print(f"       {field}: {value}")
                    else:
                        print(f"       {field}: NOT_FOUND")
        
        for trial in data:
            try:
                # Apply text search with enhanced logic
                matches_search = True  # Default to True if no search terms
                
                if search_terms:
                    matches_search = False
                    for field in search_fields:
                        if field in trial:
                            field_value = str(trial[field]).lower()
                            
                            # Enhanced search logic
                            if search_type == "exact":
                                # Exact match
                                if any(term.lower() == field_value for term in search_terms):
                                    matches_search = True
                                    break
                            elif search_type == "fuzzy":
                                # Fuzzy matching with word boundaries
                                for term in search_terms:
                                    term_words = term.lower().split()
                                    field_words = field_value.split()
                                    
                                    # Check if all term words are present in field
                                    if all(any(tw in fw for fw in field_words) for tw in term_words):
                                        matches_search = True
                                        break
                                    
                                    # Also check for substring matches
                                    if term.lower() in field_value or field_value in term.lower():
                                        matches_search = True
                                        break
                                
                                if matches_search:
                                    break
                            else:  # partial (default)
                                # Partial matching with improved logic
                                for term in search_terms:
                                    # Direct substring match
                                    if term.lower() in field_value:
                                        matches_search = True
                                        break
                                    
                                    # Word boundary matching
                                    term_words = term.lower().split()
                                    field_words = field_value.split()
                                    
                                    # Check if any term word matches any field word
                                    if any(tw in fw for tw in term_words for fw in field_words):
                                        matches_search = True
                                        break
                                
                                if matches_search:
                                    break
                
                if not matches_search:
                    continue
                
                # Apply filters with enhanced logic
                matches_filters = True
                for filter_field, filter_value in filters.items():
                    if filter_field in trial:
                        trial_value = str(trial[filter_field]).lower()
                        filter_value_lower = str(filter_value).lower()
                        
                        # Handle special filter values
                        if filter_value == "NOT_EMPTY":
                            # Check if field has any meaningful value
                            if not trial_value or trial_value.strip() == "" or trial_value in ["nan", "none", "null", "unknown", "not specified", "(n/a)"]:
                                matches_filters = False
                                break
                        elif filter_value == "HAS_BIOMARKER":
                            # Check if field contains biomarker-related content
                            biomarker_terms = ["biomarker", "marker", "mutation", "expression", "amplification", "deletion", "fusion", "rearrangement"]
                            if not any(term in trial_value for term in biomarker_terms):
                                matches_filters = False
                                break
                        elif isinstance(filter_value, list):
                            # Multiple values - any match
                            if not any(fv.lower() in trial_value for fv in filter_value):
                                matches_filters = False
                                break
                        else:
                            # Normalize multi-value OR filters separated by '|' (e.g., "Phase 2|Phase 3")
                            multi_values = [v.strip() for v in filter_value_lower.split('|') if v.strip()]
                            # Special handling for Trial Phase (arabic/roman, composite)
                            if filter_field.lower() == "trial phase":
                                tv = trial_value
                                
                                def build_aliases(val: str):
                                    numeric_to_roman = {"1": "i", "2": "ii", "3": "iii", "4": "iv"}
                                    roman_to_numeric = {v: k for k, v in numeric_to_roman.items()}
                                    val_clean = val.replace("phase ", "").strip()
                                    aliases = set()
                                    # Support composites split by '/' or ' '
                                    parts = []
                                    if "/" in val_clean:
                                        parts = [p.strip() for p in val_clean.split('/') if p.strip()]
                                    else:
                                        parts = [val_clean]
                                    for part in parts:
                                        aliases.add(part)
                                        aliases.add(f"phase {part}")
                                        if part in numeric_to_roman:
                                            r = numeric_to_roman[part]
                                            aliases.add(r)
                                            aliases.add(f"phase {r}")
                                        if part in roman_to_numeric:
                                            n = roman_to_numeric[part]
                                            aliases.add(n)
                                            aliases.add(f"phase {n}")
                                    return aliases
                                
                                # If multi_values present, any value match passes
                                if multi_values:
                                    phase_ok = False
                                    for mv in multi_values:
                                        aliases = build_aliases(mv)
                                        if any(alias in tv for alias in aliases):
                                            phase_ok = True
                                            break
                                    if not phase_ok:
                                        matches_filters = False
                                        break
                                else:
                                    aliases = build_aliases(filter_value_lower)
                                    if not any(alias in tv for alias in aliases):
                                        matches_filters = False
                                        break
                            elif filter_field.lower() == "sponsor/collaborator":
                                # Heuristic: treat 'Industry' as company sponsors (pharma/biotech) even if field doesn't literally contain 'industry'
                                if filter_value_lower == "industry":
                                    company_indicators = ["pharma", "pharmaceutical", "biotech", "inc", "corp", "co.", "company", "ltd", "llc", "gmbh", "sa", "s.a.", "plc"]
                                    sponsor_type_val = str(trial.get("Sponsor/Collaborator Type", "")).lower()
                                    # pass if: sponsor type indicates industry or sponsor name looks like a company
                                    if ("industry" not in sponsor_type_val and "top 20" not in sponsor_type_val and "pharma" not in sponsor_type_val) \
                                       and ("industry" not in trial_value) \
                                       and (not any(ci in trial_value for ci in company_indicators)):
                                        matches_filters = False
                                        break
                                else:
                                    # Generic multi-value OR for sponsor
                                    if multi_values:
                                        if not any(mv in trial_value for mv in multi_values):
                                            matches_filters = False
                                            break
                                    else:
                                        if filter_value_lower not in trial_value:
                                            matches_filters = False
                                            break
                            elif filter_field.lower() == "sponsor/collaborator type":
                                # Allow matching on type like 'Industry, Top 20 Pharma'
                                type_val = str(trial.get("Sponsor/Collaborator Type", "")).lower()
                                if multi_values:
                                    if not any(mv in type_val for mv in multi_values):
                                        matches_filters = False
                                        break
                                else:
                                    if filter_value_lower not in type_val:
                                        matches_filters = False
                                        break
                            else:
                                # Generic string contains; support multi-value OR
                                if multi_values:
                                    if not any(mv in trial_value for mv in multi_values):
                                        matches_filters = False
                                        break
                                else:
                                    if filter_value_lower not in trial_value:
                                        matches_filters = False
                                        break
                
                if matches_filters:
                    filtered_data.append(trial)
                    
            except Exception as e:
                print(f"⚠️ Error filtering trial {trial.get('Trial ID', 'unknown')}: {e}")
                continue
        
        print(f"✅ Filtered to {len(filtered_data)} trials")
        return filtered_data
    
    def _convert_to_clinical_trial_result(self, trial: Dict) -> Optional[ClinicalTrialResult]:
        """Convert TrialTrove data to ClinicalTrialResult"""
        try:
            # Helper to sanitize values for JSON serialization
            def _sanitize(obj):
                import pandas as pd
                import numpy as np
                if isinstance(obj, pd.Timestamp):
                    try:
                        return obj.strftime("%Y-%m-%d")
                    except Exception:
                        return obj.isoformat()
                if isinstance(obj, (np.integer,)):
                    return int(obj)
                if isinstance(obj, (np.floating,)):
                    return float(obj)
                if isinstance(obj, (np.bool_,)):
                    return bool(obj)
                if isinstance(obj, dict):
                    return {k: _sanitize(v) for k, v in obj.items()}
                if isinstance(obj, list):
                    return [_sanitize(v) for v in obj]
                return obj
            # Extract key information
            trial_id = str(trial.get("Trial ID", ""))
            title = trial.get("Trial Title", "")
            condition = trial.get("Disease", "")
            sponsor = trial.get("Sponsor/Collaborator", "")
            status = trial.get("Trial Status", "")
            phase = trial.get("Trial Phase", "")
            
            # Extract enrollment information
            target_accrual = trial.get("Target Accrual", "")
            actual_accrual = trial.get("Actual Accrual (No. of patients)", "")
            
            # Extract dates
            start_date = trial.get("Start Date", "")
            if start_date and pd.notna(start_date):
                if isinstance(start_date, str):
                    start_date = start_date.split()[0]  # Take first part if datetime
                else:
                    start_date = start_date.strftime("%Y-%m-%d")
            
            completion_date = trial.get("Full Completion Date", "")
            if completion_date and pd.notna(completion_date):
                if isinstance(completion_date, str):
                    completion_date = completion_date.split()[0]
                else:
                    completion_date = completion_date.strftime("%Y-%m-%d")
            
            # Extract location information
            countries = trial.get("Countries", "")
            location = countries if countries else "Not specified"
            
            # Create description with key TrialTrove-specific information
            description_parts = []
            
            # Add biomarker information
            biomarker = trial.get("Oncology Biomarker", "")
            if biomarker:
                description_parts.append(f"Biomarker: {biomarker}")
            
            # Add patient segment
            patient_segment = trial.get("Patient Segment", "")
            if patient_segment and patient_segment != "(N/A)":
                description_parts.append(f"Patient Segment: {patient_segment}")
            
            # Add inclusion criteria (do NOT truncate)
            inclusion_criteria = trial.get("Inclusion Criteria", "")
            if inclusion_criteria:
                description_parts.append(f"Inclusion Criteria: {inclusion_criteria}")
            
            # Add exclusion criteria if available (do NOT truncate)
            exclusion_criteria = trial.get("Exclusion Criteria", "")
            if exclusion_criteria:
                description_parts.append(f"Exclusion Criteria: {exclusion_criteria}")

            # Add primary endpoint
            primary_endpoint = trial.get("Primary Endpoint", "")
            if primary_endpoint:
                description_parts.append(f"Primary Endpoint: {primary_endpoint}")
            
            # Add secondary endpoint
            secondary_endpoint = trial.get("Secondary/Other Endpoint", "")
            if secondary_endpoint:
                description_parts.append(f"Secondary Endpoint: {secondary_endpoint}")

            # Add enrollment timeline
            enrollment_duration = trial.get("Enrollment Duration (Mos.)", "")
            if enrollment_duration:
                description_parts.append(f"Enrollment Duration: {enrollment_duration} months")
            
            description = " | ".join(description_parts) if description_parts else "TrialTrove data available"
            
            # Calculate relevance score based on data completeness
            relevance_score = 0.5  # Base score
            if biomarker:
                relevance_score += 0.1
            if inclusion_criteria:
                relevance_score += 0.1
            if primary_endpoint:
                relevance_score += 0.1
            if patient_segment and patient_segment != "(N/A)":
                relevance_score += 0.1
            if countries:
                relevance_score += 0.1
            
            # Attach full TrialTrove fields in metadata for downstream parsing/rendering
            metadata = {
                "trialtrove": {
                    "patient_segment": patient_segment,
                    "oncology_biomarker": biomarker,
                    "inclusion_criteria": trial.get("Inclusion Criteria", ""),
                    "exclusion_criteria": trial.get("Exclusion Criteria", ""),
                    "primary_endpoint": trial.get("Primary Endpoint", ""),
                    "secondary_endpoint": trial.get("Secondary/Other Endpoint", ""),
                    "enrollment_duration_months": enrollment_duration,
                    "countries": countries,
                    "study_design": trial.get("Study Design", ""),
                    "trial_objective": trial.get("Trial Objective", ""),
                    "raw_row": _sanitize(trial),
                }
            }

            return ClinicalTrialResult(
                nct_id=f"TrialTrove-{trial_id}",
                title=title,
                condition=condition,
                intervention=trial.get("Primary Tested Drug", ""),
                sponsor=sponsor,
                status=status,
                phase=phase,
                enrollment=target_accrual if target_accrual else None,
                start_date=start_date,
                completion_date=completion_date,
                description=description,
                location=location,
                relevance_score=min(relevance_score, 1.0),
                metadata=metadata
            )
            
        except Exception as e:
            log_error(e, f"Converting trial {trial.get('Trial ID', 'unknown')}")
            return None
    
    async def search_by_biomarker(self, biomarker: str, max_results: int = 50) -> List[ClinicalTrialResult]:
        """Search trials by biomarker"""
        await self._load_data()
        
        if not self.data:
            return []
        
        filtered_data = []
        for trial in self.data:
            trial_biomarker = trial.get("Oncology Biomarker", "")
            if biomarker.lower() in trial_biomarker.lower():
                filtered_data.append(trial)
        
        results = []
        for trial in filtered_data[:max_results]:
            result = self._convert_to_clinical_trial_result(trial)
            if result:
                results.append(result)
        
        return results
    
    async def search_by_patient_segment(self, segment: str, max_results: int = 50) -> List[ClinicalTrialResult]:
        """Search trials by patient segment"""
        await self._load_data()
        
        if not self.data:
            return []
        
        filtered_data = []
        for trial in self.data:
            patient_segment = trial.get("Patient Segment", "")
            if segment.lower() in patient_segment.lower() and patient_segment != "(N/A)":
                filtered_data.append(trial)
        
        results = []
        for trial in filtered_data[:max_results]:
            result = self._convert_to_clinical_trial_result(trial)
            if result:
                results.append(result)
        
        return results
    
    async def search_by_country(self, country: str, max_results: int = 50) -> List[ClinicalTrialResult]:
        """Search trials by country"""
        await self._load_data()
        
        if not self.data:
            return []
        
        filtered_data = []
        for trial in self.data:
            countries = trial.get("Countries", "")
            if country.lower() in countries.lower():
                filtered_data.append(trial)
        
        results = []
        for trial in filtered_data[:max_results]:
            result = self._convert_to_clinical_trial_result(trial)
            if result:
                results.append(result)
        
        return results
    
    async def search_by_endpoint(self, endpoint: str, max_results: int = 50) -> List[ClinicalTrialResult]:
        """Search trials by endpoint"""
        await self._load_data()
        
        if not self.data:
            return []
        
        filtered_data = []
        for trial in self.data:
            primary_endpoint = trial.get("Primary Endpoint", "")
            secondary_endpoint = trial.get("Secondary/Other Endpoint", "")
            
            if (endpoint.lower() in primary_endpoint.lower() or 
                endpoint.lower() in secondary_endpoint.lower()):
                filtered_data.append(trial)
        
        results = []
        for trial in filtered_data[:max_results]:
            result = self._convert_to_clinical_trial_result(trial)
            if result:
                results.append(result)
        
        return results
    
    async def get_trial_details(self, trial_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific trial"""
        await self._load_data()
        
        if not self.data:
            return None
        
        # Extract numeric ID from TrialTrove ID
        if trial_id.startswith("TrialTrove-"):
            numeric_id = trial_id.replace("TrialTrove-", "")
        else:
            numeric_id = trial_id
        
        for trial in self.data:
            if str(trial.get("Trial ID", "")) == numeric_id:
                return {
                    "trial_id": trial.get("Trial ID"),
                    "title": trial.get("Trial Title"),
                    "phase": trial.get("Trial Phase"),
                    "status": trial.get("Trial Status"),
                    "disease": trial.get("Disease"),
                    "therapeutic_area": trial.get("Therapeutic Area"),
                    "patient_segment": trial.get("Patient Segment"),
                    "biomarker": trial.get("Oncology Biomarker"),
                    "inclusion_criteria": trial.get("Inclusion Criteria"),
                    "exclusion_criteria": trial.get("Exclusion Criteria"),
                    "primary_endpoint": trial.get("Primary Endpoint"),
                    "secondary_endpoint": trial.get("Secondary/Other Endpoint"),
                    "start_date": trial.get("Start Date"),
                    "enrollment_duration": trial.get("Enrollment Duration (Mos.)"),
                    "countries": trial.get("Countries"),
                    "sponsor": trial.get("Sponsor/Collaborator"),
                    "primary_drug": trial.get("Primary Tested Drug"),
                    "drug_mechanism": trial.get("Primary Tested Drug: Mechanism Of Action"),
                    "drug_target": trial.get("Primary Tested Drug: Target"),
                    "target_accrual": trial.get("Target Accrual"),
                    "actual_accrual": trial.get("Actual Accrual (No. of patients)"),
                    "reported_sites": trial.get("Reported Sites"),
                    "study_design": trial.get("Study Design"),
                    "trial_objective": trial.get("Trial Objective")
                }
        
        return None
    
    async def get_database_statistics(self) -> Dict[str, Any]:
        """Get statistics about the TrialTrove database"""
        await self._load_data()
        
        if not self.data:
            return {"error": "No data loaded"}
        
        try:
            # Basic statistics
            total_trials = len(self.data)
            
            # Count trials by phase
            phase_counts = {}
            for trial in self.data:
                phase = trial.get("Trial Phase", "Unknown")
                phase_counts[phase] = phase_counts.get(phase, 0) + 1
            
            # Count trials by status
            status_counts = {}
            for trial in self.data:
                status = trial.get("Trial Status", "Unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            
            # Count trials with biomarkers
            biomarker_trials = sum(1 for trial in self.data if trial.get("Oncology Biomarker"))
            
            # Count trials by therapeutic area
            therapeutic_area_counts = {}
            for trial in self.data:
                area = trial.get("Therapeutic Area", "Unknown")
                therapeutic_area_counts[area] = therapeutic_area_counts.get(area, 0) + 1
            
            return {
                "total_trials": total_trials,
                "min_year": self.min_year,
                "phase_distribution": phase_counts,
                "status_distribution": status_counts,
                "biomarker_trials": biomarker_trials,
                "therapeutic_area_distribution": therapeutic_area_counts,
                "data_source": "TrialTrove CSV (2021 onwards)",
                "column_metadata": self.column_metadata if hasattr(self, 'column_metadata') else {}
            }
            
        except Exception as e:
            log_error(e, "TrialTrove statistics")
            return {"error": str(e)}
    
    async def get_column_values(self, column: str) -> List[str]:
        """Get unique values for a specific column (similar to patient profiler)"""
        await self._load_data()
        
        if not hasattr(self, 'column_metadata') or not self.column_metadata:
            return []
        
        if column in self.column_metadata:
            return self.column_metadata[column]['top_values']
        
        return []
    
    async def get_searchable_columns(self) -> List[str]:
        """Get list of searchable columns with their metadata"""
        await self._load_data()
        
        if not hasattr(self, 'column_metadata') or not self.column_metadata:
            return []
        
        return list(self.column_metadata.keys())

# Global TrialTrove agent instance
trialtrove_agent = TrialTroveAgent() 
