"""
FDA Labels Agent for FDA Structured Labels Data
Provides access to FDA drug label information including indications, contraindications, 
dosage, adverse reactions, clinical pharmacology, and more
"""
import asyncio
import pandas as pd
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from models.schemas import ClinicalTrialResult
from config import settings
from utils.logger import log_error
from utils.cache import cache_manager
from agents.llm_agent import llm_agent

class FDALabelsAgent:
    """Agent for accessing FDA Structured Labels data"""
    
    def __init__(self):
        self.data_path = Path(__file__).parent.parent / "data"
        self.excel_file = self.data_path / "FDA_Structured_Labels.xlsx"
        self.data = None
        self.loaded = False
        
    async def _load_data(self):
        """Load the Excel data"""
        if self.loaded:
            return
            
        try:
            print(f"📊 Loading FDA Labels data from {self.excel_file}")
            
            # Load Excel data
            df = pd.read_excel(self.excel_file)
            
            # Clean and prepare data
            df = df.fillna('')
            
            # Process metadata for better search
            self._process_metadata(df)
            
            # Convert to list of dictionaries for easier processing
            self.data = df.to_dict('records')
            self.loaded = True
            
            print(f"✅ Loaded {len(self.data)} FDA drug labels")
            
        except Exception as e:
            log_error(e, "FDA Labels data loading")
            print(f"❌ Error loading FDA Labels data: {e}")
            self.data = []
    
    def _process_metadata(self, df: pd.DataFrame):
        """Process metadata about the dataset for better search capabilities"""
        try:
            print("📊 Processing FDA Labels metadata for enhanced search...")
            
            # Get unique values for key searchable columns
            key_columns = [
                'manufacturer_name', 'product_name', 'generic_name', 'product_code',
                'INDICATIONS_AND_USAGE', 'CONTRAINDICATIONS', 'ADVERSE_REACTIONS',
                'DOSAGE_AND_ADMINISTRATION', 'CLINICAL_PHARMACOLOGY'
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
    
    async def search_labels(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Search for FDA drug labels"""
        await self._load_data()
        
        if not self.data:
            return []
        
        # Create cache key
        cache_key = cache_manager.get_api_cache_key("fda_labels", "labels", {"query": query, "max_results": max_results})
        
        # Check cache first
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return cached_result
        
        print(f"🔍 FDALabelsAgent.search_labels called with query: '{query}', max_results: {max_results}")
        
        try:
            # First, try direct drug name search for common drug names
            direct_results = await self.search_by_drug_name(query, max_results=max_results)
            if direct_results:
                print(f"✅ Found {len(direct_results)} results using direct drug name search")
                cache_manager.set(cache_key, direct_results)
                return direct_results
            
            # Check if we should skip LLM and go directly to fallback for common queries
            query_lower = query.lower()
            skip_llm_queries = ['obesity', 'weight', 'diabetes', 'diabetic', 'cardiovascular', 'heart', 'cancer', 'oncology', 'phase 3', 'trial']
            should_skip_llm = any(term in query_lower for term in skip_llm_queries)
            
            print(f"🔍 Query analysis: '{query}' -> should_skip_llm: {should_skip_llm}")
            
            if should_skip_llm:
                print("🔄 Skipping LLM for common query, using direct fallback...")
                fallback_drugs = self._get_fallback_drug_names(query)
                print(f"🔍 Fallback drugs found: {fallback_drugs}")
                if fallback_drugs:
                    search_criteria = {
                        "search_fields": ["product_name", "generic_name", "INDICATIONS_AND_USAGE"],
                        "search_terms": fallback_drugs[:5],
                        "filters": {},
                        "search_strategy": f"Direct fallback using real drug names: {fallback_drugs[:3]}"
                    }
                    print(f"🔄 Using direct fallback with real drugs: {search_criteria['search_terms']}")
                else:
                    print("⚠️ No fallback drugs available, falling back to LLM...")
                    # Fallback to LLM if no fallback drugs available
                    search_criteria = await self._generate_search_criteria(query)
            else:
                # Try LLM-generated search criteria
                search_criteria = await self._generate_search_criteria(query)
                print(f"🔍 Generated search criteria: {search_criteria.get('search_strategy', 'Unknown')}")
                print(f"🔍 Search terms: {search_criteria.get('search_terms', [])}")
                
                # Check if LLM generated invalid terms and force fallback
                search_terms = search_criteria.get('search_terms', [])
                print(f"🔍 Checking search terms for invalid terms: {search_terms}")
                invalid_terms = ['antiobesity', 'weight_management', 'weight_management_agent', 'glucagon_like_peptide']
                search_terms_str = ' '.join(search_terms).lower()
                print(f"🔍 Search terms string: '{search_terms_str}'")
                has_invalid_terms = any(term in search_terms_str for term in invalid_terms)
                print(f"🔍 Has invalid terms: {has_invalid_terms}")
                
                if has_invalid_terms:
                    print(f"⚠️ LLM generated invalid terms: {search_terms}")
                    print("🔄 Forcing fallback to real drug names...")
                    fallback_drugs = self._get_fallback_drug_names(query)
                    if fallback_drugs:
                        search_criteria['search_terms'] = fallback_drugs[:5]
                        search_criteria['search_strategy'] = f"Forced fallback using real drug names: {fallback_drugs[:3]}"
                        print(f"🔄 Updated search criteria with real drugs: {search_criteria['search_terms']}")
                    else:
                        print(f"⚠️ No fallback drugs available for query: {query}")
                else:
                    print(f"✅ Search terms appear valid: {search_terms}")
            
            # Filter data based on search criteria
            filtered_data = await self._filter_data_by_criteria(self.data, search_criteria)
            
            # If LLM search doesn't find relevant results, try indication search
            if not filtered_data:
                print("⚠️ LLM search found no results, trying indication search...")
                indication_results = await self.search_by_indication(query, max_results=max_results)
                if indication_results:
                    print(f"✅ Found {len(indication_results)} results using indication search")
                    cache_manager.set(cache_key, indication_results)
                    return indication_results
                
                # If indication search also fails, try fallback drug names
                print("⚠️ Indication search found no results, trying fallback drug names...")
                fallback_drugs = self._get_fallback_drug_names(query)
                if fallback_drugs:
                    print(f"🔄 Trying fallback drug names: {fallback_drugs[:3]}")
                    fallback_results = []
                    for drug in fallback_drugs[:3]:  # Try top 3 fallback drugs
                        drug_results = await self.search_by_drug_name(drug, max_results=max_results//3)
                        fallback_results.extend(drug_results)
                        if len(fallback_results) >= max_results:
                            break
                    
                    if fallback_results:
                        # Sort and limit results
                        fallback_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
                        fallback_results = fallback_results[:max_results]
                        print(f"✅ Found {len(fallback_results)} results using fallback drug names")
                        cache_manager.set(cache_key, fallback_results)
                        return fallback_results
            
            # Filter out devices - only keep drugs
            # Devices typically have indicators like: "device", "system", "kit", "implant", "stent", etc.
            drug_only_data = []
            device_keywords = ['device', 'system', 'kit', 'implant', 'stent', 'catheter', 'prosthesis', 
                             'pacemaker', 'defibrillator', 'sensor', 'monitor', 'pump', 'inhaler device',
                             'injection device', 'delivery system', 'diagnostic device', 'surgical device']
            
            for label in filtered_data:
                # Check product name, generic name, and document title for device indicators
                product_name = str(label.get('product_name', '')).lower()
                generic_name = str(label.get('generic_name', '')).lower()
                document_title = str(label.get('document_title', '')).lower()
                
                # Skip if it's clearly a device
                is_device = any(keyword in product_name or keyword in generic_name or keyword in document_title 
                              for keyword in device_keywords)
                
                # Also check if it has drug-like indicators (ingredients, dosage, etc.)
                has_drug_indicators = (
                    label.get('ingredients') or 
                    label.get('DOSAGE_AND_ADMINISTRATION') or
                    label.get('CLINICAL_PHARMACOLOGY')
                )
                
                # Include if it's not a device and has drug indicators, or if it's clearly a drug
                if not is_device and has_drug_indicators:
                    drug_only_data.append(label)
            
            # Convert to standardized format
            results = []
            for label in drug_only_data[:max_results]:
                try:
                    result = self._convert_to_standard_format(label)
                    if result:
                        results.append(result)
                except Exception as e:
                    log_error(e, f"Converting label {label.get('document_id', 'unknown')}")
                    continue
            
            # Sort by relevance score
            results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            # Cache results
            cache_manager.set(cache_key, results)
            
            print(f"✅ Found {len(results)} FDA labels")
            return results
            
        except Exception as e:
            log_error(e, "FDA Labels search")
            print(f"❌ FDA Labels search failed: {e}")
            return []
    
    def _get_fallback_drug_names(self, query: str) -> List[str]:
        """Get real drug names for common conditions as fallback"""
        query_lower = query.lower()
        
        # Obesity/Weight management drugs
        if any(term in query_lower for term in ['obesity', 'weight', 'weight loss', 'weight management']):
            return [
                'semaglutide', 'liraglutide', 'phentermine', 'topiramate', 'naltrexone', 'bupropion',
                'orlistat', 'lorcaserin', 'setmelanotide', 'tirzepatide', 'wegovy', 'ozempic',
                'saxenda', 'qsymia', 'contrave', 'xenical', 'belviq', 'imcivree'
            ]
        
        # Diabetes drugs
        if any(term in query_lower for term in ['diabetes', 'diabetic', 'glucose', 'insulin']):
            return [
                'metformin', 'insulin', 'glipizide', 'glyburide', 'pioglitazone', 'rosiglitazone',
                'sitagliptin', 'saxagliptin', 'linagliptin', 'alogliptin', 'empagliflozin',
                'canagliflozin', 'dapagliflozin', 'semaglutide', 'liraglutide', 'dulaglutide',
                'exenatide', 'lixisenatide', 'insulin glargine', 'insulin lispro', 'insulin aspart'
            ]
        
        # Cardiovascular drugs
        if any(term in query_lower for term in ['cardiovascular', 'heart', 'cardiac', 'hypertension', 'blood pressure']):
            return [
                'lisinopril', 'amlodipine', 'metoprolol', 'atenolol', 'losartan', 'valsartan',
                'simvastatin', 'atorvastatin', 'pravastatin', 'rosuvastatin', 'warfarin',
                'clopidogrel', 'aspirin', 'digoxin', 'furosemide', 'hydrochlorothiazide'
            ]
        
        # Oncology drugs
        if any(term in query_lower for term in ['cancer', 'oncology', 'tumor', 'neoplasm']):
            return [
                'pembrolizumab', 'nivolumab', 'atezolizumab', 'durvalumab', 'avelumab',
                'trastuzumab', 'bevacizumab', 'rituximab', 'cetuximab', 'panitumumab',
                'doxorubicin', 'cisplatin', 'carboplatin', 'paclitaxel', 'docetaxel'
            ]
        
        # Return empty list if no specific condition matches
        return []

    async def _generate_search_criteria(self, query: str) -> Dict[str, Any]:
        """Use LLM to generate search criteria from user query with sample data"""
        
        # Get fallback drug names for the query
        fallback_drugs = self._get_fallback_drug_names(query)
        
        # Get sample data from relevant columns
        sample_data = {}
        if hasattr(self, 'column_metadata') and self.column_metadata:
            for col in ['manufacturer_name', 'product_name', 'generic_name', 'INDICATIONS_AND_USAGE']:
                if col in self.column_metadata:
                    sample_data[col] = self.column_metadata[col]['sample_values'][:10]  # First 10 samples
        
        # If no metadata available, get some sample data directly
        if not sample_data and self.data:
            sample_labels = self.data[:5]  # First 5 labels
            sample_data = {
                'manufacturer_name': [label.get('manufacturer_name', '') for label in sample_labels if label.get('manufacturer_name')],
                'product_name': [label.get('product_name', '') for label in sample_labels if label.get('product_name')],
                'generic_name': [label.get('generic_name', '') for label in sample_labels if label.get('generic_name')],
                'INDICATIONS_AND_USAGE': [label.get('INDICATIONS_AND_USAGE', '')[:600] for label in sample_labels if label.get('INDICATIONS_AND_USAGE')]
            }
        
        prompt = f"""
You are an expert pharmaceutical analyst. Analyze the following query and generate search criteria for FDA drug labels data.

QUERY: {query}

FDA LABELS DATA FIELDS:
- document_title: Drug label title
- manufacturer_name: Drug manufacturer
- product_name: Brand name of the drug
- generic_name: Generic name of the drug
- product_code: FDA product code
- ingredients: Active ingredients
- INDICATIONS_AND_USAGE: Approved uses and indications
- CONTRAINDICATIONS: When the drug should not be used
- ADVERSE_REACTIONS: Side effects and adverse events
- DOSAGE_AND_ADMINISTRATION: How to take the drug
- CLINICAL_PHARMACOLOGY: How the drug works
- WARNINGS_AND_PRECAUTIONS: Safety warnings
- DRUG_INTERACTIONS: Drug interactions
- USE_IN_SPECIFIC_POPULATIONS: Special populations (pregnancy, elderly, etc.)
- effective_time: When the label was last updated

SAMPLE DATA FROM RELEVANT COLUMNS:
{json.dumps(sample_data, indent=2)}

FALLBACK DRUG NAMES FOR THIS QUERY:
{fallback_drugs}

INSTRUCTIONS:
1. Look at the sample data above to understand the actual format of the data
2. Generate search terms that will match the actual data format - use REAL drug names, not made-up terms
3. Use the fallback drug names provided above if they are relevant to the query
4. Identify key search terms from the query that will work with the actual data
5. Determine which fields to search in based on the query content
6. Generate appropriate search criteria that will find relevant drug labels

CRITICAL INSTRUCTIONS - FOLLOW EXACTLY:
- The search terms must match the actual format of the data shown in the samples above
- Use REAL drug names that exist in the FDA database
- NEVER use made-up terms like "weight_management_agent", "antiobesity", "weight_management", "glucagon_like_peptide", "antiobesity_agent", "weight_loss_agent"
- ALWAYS use the fallback drug names provided above if they are relevant to the query
- If the query is about obesity/weight management, you MUST use the fallback drug names like "semaglutide", "liraglutide", "phentermine", etc.
- If the query is about diabetes, you MUST use the fallback drug names like "metformin", "insulin", "empagliflozin", etc.
- If fallback drug names are provided above, you MUST use them instead of generating your own terms
- DO NOT create new terms - only use existing drug names from the samples or fallback list

FILTER VALUES:
- Use "NOT_EMPTY" to filter for fields that have any value
- Use specific drug names, conditions, or manufacturer names for exact matches
- Do NOT use "!=" or other operators - use descriptive values instead

Return ONLY valid JSON with search criteria:

{{
    "search_fields": ["field1", "field2"],
    "search_terms": ["term1", "term2"],
    "filters": {{
        "field_name": "value_or_condition"
    }},
    "search_strategy": "description of search approach"
}}
"""
        
        response = await llm_agent.generate_structured_response(
            prompt,
            system_prompt="You are an expert pharmaceutical analyst. Generate precise search criteria for FDA drug labels using REAL drug names. NEVER use made-up terms like 'antiobesity', 'weight_management', 'weight_management_agent', 'glucagon_like_peptide', 'antiobesity_agent', or 'weight_loss_agent'. ALWAYS use the fallback drug names provided in the prompt. If fallback drug names are provided, you MUST use them instead of generating your own terms. Always return valid JSON."
        )
        
        try:
            criteria = json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                criteria = json.loads(json_match.group())
            else:
                # Enhanced fallback with real drug names
                criteria = {
                    "search_fields": ["product_name", "generic_name", "INDICATIONS_AND_USAGE"],
                    "search_terms": fallback_drugs[:5] if fallback_drugs else query.split(),
                    "filters": {},
                    "search_strategy": f"Fallback search using real drug names: {fallback_drugs[:3] if fallback_drugs else 'simple keywords'}"
                }
        
        return criteria
    
    async def _filter_data_by_criteria(self, data: List[Dict], criteria: Dict) -> List[Dict]:
        """Filter data based on search criteria"""
        try:
            filtered_data = []
            search_fields = criteria.get("search_fields", [])
            search_terms = criteria.get("search_terms", [])
            filters = criteria.get("filters", {})
            
            for item in data:
                relevance_score = 0
                matches = 0
                
                # Apply search terms
                for field in search_fields:
                    if field in item:
                        field_value = str(item[field]).lower()
                        for term in search_terms:
                            if term.lower() in field_value:
                                relevance_score += 1
                                matches += 1
                
                # Apply filters
                filter_matches = True
                for field, value in filters.items():
                    if field in item:
                        if value == "NOT_EMPTY":
                            if not item[field] or str(item[field]).strip() == "":
                                filter_matches = False
                        else:
                            if str(value).lower() not in str(item[field]).lower():
                                filter_matches = False
                    else:
                        filter_matches = False
                
                if filter_matches and matches > 0:
                    item['relevance_score'] = relevance_score
                    filtered_data.append(item)
            
            return filtered_data
            
        except Exception as e:
            log_error(e, "FDA Labels data filtering")
            return []
    
    def _convert_to_standard_format(self, label: Dict) -> Optional[Dict[str, Any]]:
        """Convert FDA label data to standardized format"""
        try:
            # Extract key information
            result = {
                'id': label.get('document_id', ''),
                'title': label.get('document_title', ''),
                'manufacturer': label.get('manufacturer_name', ''),
                'product_name': label.get('product_name', ''),
                'generic_name': label.get('generic_name', ''),
                'product_code': label.get('product_code', ''),
                'ingredients': label.get('ingredients', ''),
                'effective_time': label.get('effective_time', ''),
                'indications': label.get('INDICATIONS_AND_USAGE', ''),
                'contraindications': label.get('CONTRAINDICATIONS', ''),
                'adverse_reactions': label.get('ADVERSE_REACTIONS', ''),
                'dosage': label.get('DOSAGE_AND_ADMINISTRATION', ''),
                'clinical_pharmacology': label.get('CLINICAL_PHARMACOLOGY', ''),
                'warnings': label.get('WARNINGS_AND_PRECAUTIONS', ''),
                'drug_interactions': label.get('DRUG_INTERACTIONS', ''),
                'specific_populations': label.get('USE_IN_SPECIFIC_POPULATIONS', ''),
                'relevance_score': label.get('relevance_score', 0),
                'source': 'FDA Labels',
                'url': f"https://www.accessdata.fda.gov/drugsatfda_docs/label/{label.get('effective_time', '')}/{label.get('product_code', '')}lbl.pdf" if label.get('effective_time') and label.get('product_code') else None
            }
            
            return result
            
        except Exception as e:
            log_error(e, f"Converting FDA label {label.get('document_id', 'unknown')}")
            return None
    
    def _is_device(self, label: Dict) -> bool:
        """Check if a label is for a device rather than a drug"""
        device_keywords = ['device', 'system', 'kit', 'implant', 'stent', 'catheter', 'prosthesis', 
                          'pacemaker', 'defibrillator', 'sensor', 'monitor', 'pump', 'inhaler device',
                          'injection device', 'delivery system', 'diagnostic device', 'surgical device']
        
        product_name = str(label.get('product_name', '')).lower()
        generic_name = str(label.get('generic_name', '')).lower()
        document_title = str(label.get('document_title', '')).lower()
        
        # Check if it's clearly a device
        is_device = any(keyword in product_name or keyword in generic_name or keyword in document_title 
                       for keyword in device_keywords)
        
        # Also check if it has drug-like indicators
        has_drug_indicators = (
            label.get('ingredients') or 
            label.get('DOSAGE_AND_ADMINISTRATION') or
            label.get('CLINICAL_PHARMACOLOGY')
        )
        
        # It's a device if it has device keywords AND lacks drug indicators
        return is_device and not has_drug_indicators
    
    async def _get_drug_variations(self, drug_name: str) -> List[str]:
        """Intelligently get drug name variations using LLM and data analysis"""
        drug_name_lower = drug_name.lower().strip()
        variations = [drug_name_lower]  # Always include the original search term
        
        # Use LLM to extract and suggest drug name variations
        try:
            await self._load_data()
            if not self.data:
                return variations
            
            # Get sample drug names from the data to help LLM understand the format
            sample_drugs = []
            for label in self.data[:50]:  # Sample first 50 labels
                product = str(label.get('product_name', '')).strip()
                generic = str(label.get('generic_name', '')).strip()
                if product and product not in sample_drugs:
                    sample_drugs.append(product)
                if generic and generic not in sample_drugs:
                    sample_drugs.append(generic)
                if len(sample_drugs) >= 20:
                    break
            
            prompt = f"""You are a pharmaceutical expert. Given a drug name query, identify all possible variations, brand names, and generic names that might be used in FDA drug labels.

Query: "{drug_name}"

Based on pharmaceutical naming conventions, provide:
1. The exact query term
2. Common brand names for this drug (if it's a generic name)
3. Generic name (if it's a brand name)
4. Common misspellings or variations
5. Related drug names in the same class

Sample drug names from FDA labels (for reference):
{', '.join(sample_drugs[:10])}

Return ONLY a JSON array of drug name variations, like:
["drug_name_1", "drug_name_2", "drug_name_3"]

Do not include explanations, just the JSON array."""
            
            system_prompt = "You are a pharmaceutical expert. Return only valid JSON array of drug name variations."
            response = await llm_agent.generate_structured_response(prompt, system_prompt)
            
            try:
                # Try to parse JSON array
                json_match = re.search(r'\[[\s\S]*\]', response)
                if json_match:
                    parsed_variations = json.loads(json_match.group())
                    if isinstance(parsed_variations, list):
                        variations.extend([v.lower().strip() for v in parsed_variations if v])
                else:
                    # Try direct JSON parse
                    parsed_variations = json.loads(response)
                    if isinstance(parsed_variations, list):
                        variations.extend([v.lower().strip() for v in parsed_variations if v])
            except:
                # If LLM parsing fails, fall back to intelligent substring search
                pass
        except Exception as e:
            print(f"⚠️ Error getting drug variations from LLM: {e}")
        
        # Also do intelligent data-driven expansion: search the actual data for similar names
        try:
            await self._load_data()
            if self.data:
                # Find drugs with similar names in the data
                for label in self.data[:200]:  # Check first 200 labels for performance
                    product = str(label.get('product_name', '')).lower()
                    generic = str(label.get('generic_name', '')).lower()
                    
                    # If query is substring of product/generic or vice versa
                    if drug_name_lower in product or product in drug_name_lower:
                        if product and product not in variations:
                            variations.append(product)
                    if drug_name_lower in generic or generic in drug_name_lower:
                        if generic and generic not in variations:
                            variations.append(generic)
                    
                    # Limit variations to avoid too many
                    if len(variations) >= 10:
                        break
        except Exception as e:
            print(f"⚠️ Error in data-driven expansion: {e}")
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for var in variations:
            var_clean = var.lower().strip()
            if var_clean and var_clean not in seen:
                seen.add(var_clean)
                unique_variations.append(var_clean)
        
        return unique_variations[:10]  # Limit to 10 variations for performance
    
    async def search_by_drug_name(self, drug_name: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Search for labels by drug name (brand or generic) - intelligently finds variations"""
        await self._load_data()
        
        if not self.data:
            return []
        
        try:
            results = []
            dn = (drug_name or "").strip()
            dn = re.sub(r"',\s*max_results\s*:\s*\d+.*$", "", dn, flags=re.I).strip()
            dn = dn.strip("'\"").split("\n")[0][:500].strip()
            if not dn:
                return []
            drug_name = dn
            drug_name_lower = drug_name.lower().strip()
            
            # Intelligently get drug name variations
            search_terms = await self._get_drug_variations(drug_name)
            print(f"🔍 Searching FDA labels for '{drug_name}' with intelligent variations: {search_terms[:5]}")
            
            for label in self.data:
                # Skip devices - only process drugs
                if self._is_device(label):
                    continue
                
                relevance_score = 0
                product_name = str(label.get('product_name', '')).lower()
                generic_name = str(label.get('generic_name', '')).lower()
                ingredients = str(label.get('ingredients', '')).lower()
                
                # Check all variations with intelligent scoring
                for term in search_terms:
                    term_lower = term.lower().strip()
                    if not term_lower:
                        continue
                    
                    # Exact match in product name (highest relevance)
                    if product_name and term_lower == product_name:
                        relevance_score += 10
                    # Exact match in generic name
                    elif generic_name and term_lower == generic_name:
                        relevance_score += 9
                    # Product name contains term (word boundary aware)
                    elif product_name and term_lower in product_name:
                        # Check if it's a word boundary match (not just substring)
                        if re.search(r'\b' + re.escape(term_lower) + r'\b', product_name):
                            relevance_score += 7
                        else:
                            relevance_score += 5
                    # Generic name contains term
                    elif generic_name and term_lower in generic_name:
                        if re.search(r'\b' + re.escape(term_lower) + r'\b', generic_name):
                            relevance_score += 6
                        else:
                            relevance_score += 4
                    # Match in ingredients (lower relevance)
                    elif ingredients and term_lower in ingredients:
                        relevance_score += 2
                
                if relevance_score > 0:
                    label['relevance_score'] = relevance_score
                    result = self._convert_to_standard_format(label)
                    if result:
                        results.append(result)
            
            # Sort by relevance and limit results
            results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            print(f"✅ Found {len(results)} FDA labels for '{drug_name}'")
            return results[:max_results]
            
        except Exception as e:
            log_error(e, "FDA Labels drug name search")
            return []
    
    async def search_by_indication(self, indication: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Search for labels by medical indication"""
        await self._load_data()
        
        if not self.data:
            return []
        
        try:
            results = []
            indication_lower = indication.lower()
            
            for label in self.data:
                # Skip devices - only process drugs
                if self._is_device(label):
                    continue
                
                relevance_score = 0
                
                # Check indications and usage
                if indication_lower in str(label.get('INDICATIONS_AND_USAGE', '')).lower():
                    relevance_score += 3
                
                # Check clinical pharmacology
                if indication_lower in str(label.get('CLINICAL_PHARMACOLOGY', '')).lower():
                    relevance_score += 1
                
                if relevance_score > 0:
                    label['relevance_score'] = relevance_score
                    result = self._convert_to_standard_format(label)
                    if result:
                        results.append(result)
            
            # Sort by relevance and limit results
            results.sort(key=lambda x: x['relevance_score'], reverse=True)
            return results[:max_results]
            
        except Exception as e:
            log_error(e, "FDA Labels indication search")
            return []
    
    async def search_by_manufacturer(self, manufacturer: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Search for labels by manufacturer"""
        await self._load_data()
        
        if not self.data:
            return []
        
        try:
            results = []
            manufacturer_lower = manufacturer.lower()
            
            for label in self.data:
                if manufacturer_lower in str(label.get('manufacturer_name', '')).lower():
                    label['relevance_score'] = 1
                    result = self._convert_to_standard_format(label)
                    if result:
                        results.append(result)
            
            return results[:max_results]
            
        except Exception as e:
            log_error(e, "FDA Labels manufacturer search")
            return []
    
    async def get_label_details(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information for a specific label"""
        await self._load_data()
        
        if not self.data:
            return None
        
        try:
            for label in self.data:
                if label.get('document_id') == document_id:
                    return self._convert_to_standard_format(label)
            
            return None
            
        except Exception as e:
            log_error(e, f"Getting FDA label details for {document_id}")
            return None
    
    async def get_database_statistics(self) -> Dict[str, Any]:
        """Get statistics about the FDA labels database"""
        await self._load_data()
        
        if not self.data:
            return {"error": "No data loaded"}
        
        try:
            # Get unique manufacturers
            manufacturers = set()
            products = set()
            generics = set()
            
            for label in self.data:
                if label.get('manufacturer_name'):
                    manufacturers.add(label['manufacturer_name'])
                if label.get('product_name'):
                    products.add(label['product_name'])
                if label.get('generic_name'):
                    generics.add(label['generic_name'])
            
            return {
                "total_labels": len(self.data),
                "unique_manufacturers": len(manufacturers),
                "unique_products": len(products),
                "unique_generics": len(generics),
                "data_source": "FDA Structured Labels",
                "last_updated": "2024"
            }
            
        except Exception as e:
            log_error(e, "Getting FDA Labels statistics")
            return {"error": str(e)}
    
    async def get_column_values(self, column: str) -> List[str]:
        """Get unique values for a specific column"""
        await self._load_data()
        
        if not self.data:
            return []
        
        try:
            values = set()
            for label in self.data:
                if column in label and label[column]:
                    values.add(str(label[column]))
            
            return sorted(list(values))
            
        except Exception as e:
            log_error(e, f"Getting FDA Labels column values for {column}")
            return []
    
    async def get_searchable_columns(self) -> List[str]:
        """Get list of searchable columns"""
        return [
            'document_title', 'manufacturer_name', 'product_name', 'generic_name',
            'product_code', 'ingredients', 'INDICATIONS_AND_USAGE', 'CONTRAINDICATIONS',
            'ADVERSE_REACTIONS', 'DOSAGE_AND_ADMINISTRATION', 'CLINICAL_PHARMACOLOGY',
            'WARNINGS_AND_PRECAUTIONS', 'DRUG_INTERACTIONS', 'USE_IN_SPECIFIC_POPULATIONS'
        ]

# Create singleton instance
fda_labels_agent = FDALabelsAgent() 