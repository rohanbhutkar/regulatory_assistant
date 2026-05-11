from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from api_models import TrialTroveFilters, SiteTroveFilters, ClaimsFilters
import pandas as pd
import numpy as np
from utils.json_utils import dataframe_to_dict_safe
from utils.enhanced_smart_search import enhanced_smart_search_trials

router = APIRouter()

# This will be populated by the data loader
data_loader = None

def set_data_loader(loader):
    global data_loader
    data_loader = loader

@router.post("/trialtrove")
async def search_trialtrove_data(request: Dict[str, Any]):
    """Search TrialTrove data with query and filters using LLM-powered smart search"""
    try:
        if not data_loader:
            raise HTTPException(status_code=500, detail="Data loader not initialized")
        
        query = request.get("query", "")
        limit = request.get("limit", 100)
        use_smart_search = request.get("use_smart_search", True)  # Enable by default
        
        # Get TrialTrove data
        trialtrove_df = data_loader.get_data('trialtrove')
        
        if trialtrove_df.empty:
            return {"trials": [], "total": 0, "message": "No TrialTrove data available"}
        
        # Search for trials matching the query
        if query and use_smart_search:
            print(f"🤖 Using Enhanced LLM-powered smart search with full column awareness for: '{query}'")
            filtered_df, metadata = await enhanced_smart_search_trials(trialtrove_df, query, use_llm=True)
            print(f"📊 Enhanced smart search found {len(filtered_df)} matching trials out of {len(trialtrove_df)} total")
            print(f"   Interpretation: {metadata.get('interpretation', 'N/A')}")
            print(f"   Columns searched: {', '.join(metadata.get('columns_searched', []))}")
            print(f"   Filters applied: {', '.join(metadata.get('filters_applied', []))}")
        elif query:
            # Split query into individual terms for AND logic
            query_terms = query.lower().split()
            
            # Define smart column mappings for specific terms FIRST
            # Format: {term_pattern: (column_name, use_exact_match, normalized_values)}
            smart_mappings = {
                # Phase mappings
                'i': ('Trial Phase', True, {'i': 'I', 'ii': 'II', 'iii': 'III', 'iv': 'IV'}),
                'ii': ('Trial Phase', True, {'i': 'I', 'ii': 'II', 'iii': 'III', 'iv': 'IV'}),
                'iii': ('Trial Phase', True, {'i': 'I', 'ii': 'II', 'iii': 'III', 'iv': 'IV'}),
                'iv': ('Trial Phase', True, {'i': 'I', 'ii': 'II', 'iii': 'III', 'iv': 'IV'}),
                '1': ('Trial Phase', True, {'1': 'I', '2': 'II', '3': 'III', '4': 'IV'}),
                '2': ('Trial Phase', True, {'1': 'I', '2': 'II', '3': 'III', '4': 'IV'}),
                '3': ('Trial Phase', True, {'1': 'I', '2': 'II', '3': 'III', '4': 'IV'}),
                '4': ('Trial Phase', True, {'1': 'I', '2': 'II', '3': 'III', '4': 'IV'}),
                # Status mappings (matching actual data values)
                'active': ('Trial Status', True, {'active': 'Open'}),  # Map 'active' to 'Open'
                'open': ('Trial Status', True, None),
                'completed': ('Trial Status', True, None),
                'recruiting': ('Trial Status', True, {'recruiting': 'Open'}),  # Map 'recruiting' to 'Open'
                'terminated': ('Trial Status', True, None),
                'closed': ('Trial Status', True, None),
                'planned': ('Trial Status', True, None),
            }
            
            # Remove common stopwords that don't add meaning
            # Don't remove terms that have smart mappings
            stopwords = ['phase', 'trial', 'trials', 'study', 'studies', 'the', 'a', 'an', 'and', 'or', 'of', 'in', 'on', 'at', 'with', 'for']
            query_terms = [term for term in query_terms if term not in stopwords or term in smart_mappings]
            
            print(f"🔍 Search query: '{query}' -> terms after stopword removal: {query_terms}")
            
            # Start with all trials
            filtered_df = trialtrove_df
            
            # Broad search columns for non-specific terms
            broad_search_columns = [
                'Trial Title',
                'Therapeutic Area',
                'Disease',
                'Sponsor/Collaborator',
                'Protocol/Trial ID',
                'Patient Segment',
                'MeSH Term',
                'Primary Tested Drug',
                'Patient Population',
                'Inclusion Criteria',
                'Exclusion Criteria'
            ]
            
            # Process each term
            for term in query_terms:
                term_mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
                
                # Check if this term has a smart mapping
                if term in smart_mappings:
                    col_name, use_exact, value_map = smart_mappings[term]
                    
                    if col_name in filtered_df.columns:
                        # Normalize the term if mapping exists
                        search_value = value_map[term] if value_map else term
                        
                        print(f"  🎯 Smart filter on '{col_name}' for term '{term}' -> '{search_value}'")
                        
                        # Use word boundary for exact match
                        if use_exact:
                            term_mask = filtered_df[col_name].astype(str).str.contains(
                                f'\\b{search_value}\\b', case=False, na=False, regex=True
                            )
                        else:
                            term_mask = filtered_df[col_name].astype(str).str.lower().str.contains(
                                search_value.lower(), case=False, na=False, regex=False
                            )
                else:
                    # Broad search across multiple columns
                    print(f"  🔍 Broad search for term '{term}'")
                    
                    for col in broad_search_columns:
                        if col in filtered_df.columns:
                            col_matches = filtered_df[col].astype(str).str.lower().str.contains(
                                term, case=False, na=False, regex=False
                            )
                            term_mask = term_mask | col_matches
                
                # Apply AND logic: keep only rows that match this term
                filtered_df = filtered_df[term_mask]
                print(f"  ✓ After filtering by '{term}': {len(filtered_df)} trials remain")
            
            print(f"📊 Found {len(filtered_df)} matching trials out of {len(trialtrove_df)} total")
        else:
            filtered_df = trialtrove_df
        
        # Limit results
        if len(filtered_df) > limit:
            filtered_df = filtered_df.head(limit)
        
        # Convert to list of dictionaries
        trials = dataframe_to_dict_safe(filtered_df)
        
        return {
            "trials": trials,
            "total": len(trials),
            "query": query,
            "message": f"Found {len(trials)} trials matching '{query}'"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching trials: {str(e)}")

@router.get("/trialtrove")
async def get_trialtrove_data(
    query: Optional[str] = None,
    therapeutic_area: Optional[str] = None,
    phase: Optional[str] = None,
    limit: int = 50
):
    """Get TrialTrove data using existing agent"""
    try:
        if not data_loader:
            raise HTTPException(status_code=500, detail="Data loader not initialized")
        
        # Build search parameters
        search_params = {}
        if query:
            search_params['search_term'] = query
        if therapeutic_area:
            search_params['therapeutic_area'] = therapeutic_area
        if phase:
            search_params['phase'] = phase
        
        # Use data loader to search data
        results = data_loader.search_trials(search_params)
        
        return {
            "trials": dataframe_to_dict_safe(results.head(limit)),
            "total_count": len(results),
            "search_params": search_params
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sitetrove")
async def get_sitetrove_data(
    query: Optional[str] = None,
    site_type: Optional[str] = None,
    therapeutic_area: Optional[str] = None,
    limit: int = 50
):
    """Get SiteTrove data using existing agent"""
    try:
        if not data_loader:
            raise HTTPException(status_code=500, detail="Data loader not initialized")
        
        search_params = {}
        if query:
            search_params['search_term'] = query
        if site_type:
            search_params['site_type'] = site_type
        if therapeutic_area:
            search_params['therapeutic_area'] = therapeutic_area
        
        results = data_loader.search_sites(search_params)
        
        return {
            "sites": dataframe_to_dict_safe(results.head(limit)),
            "total_count": len(results),
            "search_params": search_params
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/claims/population-analysis")
async def analyze_population(criteria: List[Dict[str, Any]]):
    """Analyze population using claims data agent"""
    try:
        if not data_loader:
            raise HTTPException(status_code=500, detail="Data loader not initialized")
        
        # Get claims data
        claims_data = data_loader.get_claims_data()
        
        if claims_data.empty:
            return {
                "initial_population": 0,
                "filtered_population": 0,
                "geographic_distribution": {},
                "demographic_breakdown": {},
                "cost_analysis": {}
            }
        
        # Mock population analysis based on criteria
        initial_population = len(claims_data)
        filtered_population = int(initial_population * 0.6)  # Mock filtering
        
        return {
            "initial_population": initial_population,
            "filtered_population": filtered_population,
            "geographic_distribution": {
                "North America": int(filtered_population * 0.4),
                "Europe": int(filtered_population * 0.3),
                "Asia": int(filtered_population * 0.2),
                "Other": int(filtered_population * 0.1)
            },
            "demographic_breakdown": {
                "age_18_65": int(filtered_population * 0.7),
                "age_65_plus": int(filtered_population * 0.3),
                "male": int(filtered_population * 0.52),
                "female": int(filtered_population * 0.48)
            },
            "cost_analysis": {
                "average_cost_per_patient": 15000,
                "total_cost": filtered_population * 15000,
                "cost_by_payer": {
                    "commercial": filtered_population * 15000 * 0.4,
                    "medicare": filtered_population * 15000 * 0.35,
                    "medicaid": filtered_population * 15000 * 0.25
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/simulation/startup")
async def run_startup_simulation(simulation_params: Dict[str, Any]):
    """Run startup simulation using existing simulation agent"""
    try:
        # Mock simulation results
        return {
            "simulation_id": "sim_001",
            "enrollment_curves": [
                {"month": 1, "enrollment": 5, "cumulative": 5},
                {"month": 2, "enrollment": 12, "cumulative": 17},
                {"month": 3, "enrollment": 18, "cumulative": 35},
                {"month": 4, "enrollment": 25, "cumulative": 60},
                {"month": 5, "enrollment": 30, "cumulative": 90},
                {"month": 6, "enrollment": 35, "cumulative": 125}
            ],
            "key_timepoints": [
                {"milestone": "First Patient In", "estimated_date": "2024-02-15"},
                {"milestone": "Last Patient In", "estimated_date": "2024-08-15"},
                {"milestone": "Study Completion", "estimated_date": "2025-06-15"}
            ],
            "sensitivity_analysis": {
                "screen_failure_rate": {"baseline": 0.2, "impact": "±2 months"},
                "site_activation": {"baseline": 0.8, "impact": "±1 month"},
                "enrollment_rate": {"baseline": 0.6, "impact": "±3 months"}
            },
            "risk_factors": [
                {"factor": "Regulatory delays", "probability": 0.3, "impact": "High"},
                {"factor": "Site activation delays", "probability": 0.4, "impact": "Medium"},
                {"factor": "Patient recruitment challenges", "probability": 0.2, "impact": "High"}
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/payer")
async def get_payer_data(
    analysis_type: str = "market_analysis",
    therapeutic_area: Optional[str] = None,
    indication: Optional[str] = None
):
    """Get payer data for analysis"""
    try:
        if not data_loader:
            raise HTTPException(status_code=500, detail="Data loader not initialized")
        
        # Get payer data
        payer_data = data_loader.get_payer_data("Customer_Dim")
        
        if payer_data.empty:
            return {
                "market_size": 2500000000,
                "payer_coverage": 0.85,
                "market_penetration": 0.12,
                "competitive_landscape": [
                    {"competitor": "Competitor A", "market_share": 0.35},
                    {"competitor": "Competitor B", "market_share": 0.28},
                    {"competitor": "Competitor C", "market_share": 0.22}
                ]
            }
        
        # Mock payer analysis
        return {
            "market_size": 2500000000,
            "payer_coverage": 0.85,
            "market_penetration": 0.12,
            "payer_split": {
                "commercial": 0.4,
                "medicare": 0.35,
                "medicaid": 0.25
            },
            "competitive_landscape": [
                {"competitor": "Competitor A", "market_share": 0.35, "pricing": 1200},
                {"competitor": "Competitor B", "market_share": 0.28, "pricing": 1100},
                {"competitor": "Competitor C", "market_share": 0.22, "pricing": 1300}
            ],
            "coverage_trends": {
                "commercial_coverage": 0.8,
                "medicare_coverage": 0.9,
                "medicaid_coverage": 0.7,
                "time_to_coverage": 12
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/icd-population-analysis")
async def analyze_icd_population(request: Dict[str, Any]):
    """
    Analyze population size and impact for specific ICD-10 codes or conditions
    
    Request body:
    {
        "icd_codes": ["C34.90", "C79.31"],  // Optional: specific ICD codes
        "condition": "NSCLC",                // Optional: condition name
        "criterion_text": "brain metastases" // Optional: criterion text for keyword matching
    }
    
    Returns:
    {
        "icd_code": "C34.90",
        "description": "Non-small cell lung cancer",
        "total_patients": 850000,
        "prevalence_rate": 0.0026,
        "impact_percentage": 0.85,
        "reasoning": "Based on 850,000 patients with C34.90 in claims database",
        "geographic_distribution": {...},
        "demographics": {...}
    }
    """
    try:
        if not data_loader:
            raise HTTPException(status_code=500, detail="Claims data not available")
        
        icd_codes = request.get("icd_codes", [])
        condition = request.get("condition", "")
        criterion_text = request.get("criterion_text", "")
        
        # Get claims data from the optimized data loader
        claims_df = data_loader.get_data('claims')
        
        if claims_df is None or claims_df.empty:
            raise HTTPException(status_code=500, detail="Claims data not loaded")
        
        results = []
        
        # If specific ICD codes provided, analyze them
        if icd_codes:
            for icd_code in icd_codes:
                result = await _analyze_single_icd(claims_df, icd_code, None)
                if result:
                    results.append(result)
        
        # If condition or criterion text provided, search for matching ICDs
        elif condition or criterion_text:
            search_text = condition or criterion_text
            matching_icds = await _search_icd_codes(claims_df, search_text, None)
            
            for icd_data in matching_icds[:5]:  # Top 5 matches
                result = await _analyze_single_icd(claims_df, icd_data['code'], None)
                if result:
                    results.append(result)
        
        if not results:
            # Return empty result with message
            return {
                "results": [],
                "message": "No matching ICD codes found in claims data"
            }
        
        return {
            "results": results,
            "total_results": len(results)
        }
        
    except Exception as e:
        import traceback
        print(f"Error in ICD population analysis: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

async def _analyze_single_icd(claims_df: pd.DataFrame, icd_code: str, claims_agent) -> Optional[Dict[str, Any]]:
    """Analyze a single ICD code from claims data"""
    try:
        # Count patients with this ICD code
        # Check all diagnosis columns (D1, D2, D3, etc.)
        diagnosis_cols = [col for col in claims_df.columns if col.startswith('D') and col != 'DIAGNOSIS_CODE']
        
        if not diagnosis_cols:
            # Try DIAGNOSIS_CODE column
            diagnosis_cols = ['DIAGNOSIS_CODE'] if 'DIAGNOSIS_CODE' in claims_df.columns else []
        
        if not diagnosis_cols:
            return None
        
        # Find rows with this ICD code in any diagnosis column
        mask = pd.Series([False] * len(claims_df))
        for col in diagnosis_cols:
            mask |= claims_df[col].astype(str).str.contains(icd_code, case=False, na=False)
        
        matching_claims = claims_df[mask]
        
        if matching_claims.empty:
            return None
        
        # Count unique patients
        patient_col = 'PATIENT_ID' if 'PATIENT_ID' in matching_claims.columns else 'Patient_ID'
        if patient_col not in matching_claims.columns:
            # Use row count as proxy
            total_patients = len(matching_claims)
        else:
            total_patients = matching_claims[patient_col].nunique()
        
        # EXTRAPOLATE TO FULL US POPULATION
        # Claims database represents ~15% sample of US population
        # All patient counts are extrapolated to full US population (330M)
        claims_sample_rate = 0.15  # 15% sample rate
        estimated_us_population = total_patients / claims_sample_rate
        
        # Get description from reference data
        description = _get_icd_description(icd_code, None)
        
        # Calculate impact percentage (what % of total US population has this condition)
        us_total_population = 330000000  # US population
        impact_percentage = estimated_us_population / us_total_population
        
        # Geographic distribution
        geographic_dist = _get_geographic_distribution(matching_claims)
        
        # Demographics
        demographics = _get_demographics(matching_claims)
        
        return {
            "icd_code": icd_code,
            "description": description,
            "total_patients_in_claims": total_patients,
            "estimated_us_patients": int(estimated_us_population),
            "impact_percentage": round(impact_percentage, 4),
            "prevalence_rate": round(impact_percentage * 100, 2),  # As percentage
            "reasoning": f"Based on {total_patients:,} patients with {icd_code} in claims database (est. {int(estimated_us_population):,} US patients)",
            "geographic_distribution": geographic_dist,
            "demographics": demographics
        }
        
    except Exception as e:
        print(f"Error analyzing ICD {icd_code}: {str(e)}")
        return None

async def _search_icd_codes(claims_df: pd.DataFrame, search_text: str, claims_agent) -> List[Dict[str, Any]]:
    """Search for ICD codes matching the search text"""
    try:
        # Simple search in diagnosis columns of claims data
        search_lower = search_text.lower()
        diagnosis_cols = [col for col in claims_df.columns if col.startswith('D') and col != 'DIAGNOSIS_CODE']
        
        if not diagnosis_cols:
            diagnosis_cols = ['DIAGNOSIS_CODE'] if 'DIAGNOSIS_CODE' in claims_df.columns else []
        
        # Get unique ICD codes from claims data
        icd_codes = set()
        for col in diagnosis_cols:
            codes = claims_df[col].dropna().unique()
            for code in codes:
                if search_lower in str(code).lower():
                    icd_codes.add(str(code))
        
        return [
            {"code": code, "description": f"ICD-10: {code}"}
            for code in list(icd_codes)[:10]
        ]
        
    except Exception as e:
        print(f"Error searching ICD codes: {str(e)}")
        return []

def _get_icd_description(icd_code: str, claims_agent) -> str:
    """Get description for an ICD code"""
    # Simple mapping of common ICD codes
    icd_descriptions = {
        'C34': 'Malignant neoplasm of bronchus and lung',
        'C34.9': 'Malignant neoplasm of bronchus or lung, unspecified',
        'C34.90': 'Malignant neoplasm of unspecified part of unspecified bronchus or lung',
        'C34.91': 'Malignant neoplasm of unspecified part of right bronchus or lung',
        'C34.92': 'Malignant neoplasm of unspecified part of left bronchus or lung',
        'E11': 'Type 2 diabetes mellitus',
        'I10': 'Essential (primary) hypertension',
        'J45': 'Asthma',
    }
    
    # Try exact match
    if icd_code in icd_descriptions:
        return icd_descriptions[icd_code]
    
    # Try prefix match (e.g., C34.9 → C34)
    for prefix_len in range(len(icd_code), 0, -1):
        prefix = icd_code[:prefix_len]
        if prefix in icd_descriptions:
            return icd_descriptions[prefix]
    
    # Fallback
    return f"ICD-10: {icd_code}"

def _get_geographic_distribution(claims_df: pd.DataFrame) -> Dict[str, Any]:
    """Get geographic distribution from claims"""
    try:
        if 'STATE' in claims_df.columns:
            state_counts = claims_df['STATE'].value_counts().head(10).to_dict()
            return {
                "top_states": state_counts,
                "total_states": claims_df['STATE'].nunique()
            }
        return {}
    except Exception:
        return {}

def _get_demographics(claims_df: pd.DataFrame) -> Dict[str, Any]:
    """Get demographics from claims"""
    try:
        demographics = {}
        
        # Age distribution
        if 'AGE' in claims_df.columns:
            demographics['age_mean'] = float(claims_df['AGE'].mean())
            demographics['age_median'] = float(claims_df['AGE'].median())
            demographics['age_range'] = {
                "min": int(claims_df['AGE'].min()),
                "max": int(claims_df['AGE'].max())
            }
        
        # Gender distribution
        if 'GENDER' in claims_df.columns or 'SEX' in claims_df.columns:
            gender_col = 'GENDER' if 'GENDER' in claims_df.columns else 'SEX'
            gender_counts = claims_df[gender_col].value_counts().to_dict()
            demographics['gender_distribution'] = gender_counts
        
        return demographics
    except Exception:
        return {}

