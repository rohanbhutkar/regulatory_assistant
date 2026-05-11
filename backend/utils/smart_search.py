"""
Smart search utilities using LLM to understand query intent and match trials semantically
"""
from typing import List, Dict, Any, Tuple
import pandas as pd
from agents.llm_agent import llm_agent

async def analyze_search_query(query: str) -> Dict[str, Any]:
    """
    Use LLM to analyze the search query and extract structured search criteria
    
    Returns:
        Dict with keys: indication, phase, status, therapeutic_area, keywords
    """
    
    prompt = f"""Analyze this clinical trial search query and extract structured search criteria.

Query: "{query}"

Extract the following information:
1. **Primary Indication/Disease**: The main disease or condition being studied
2. **Phase**: Clinical trial phase (I, II, III, IV, or combinations like "II/III")
3. **Trial Status**: Trial status if mentioned (e.g., active, recruiting, completed)
4. **Therapeutic Area**: Broader therapeutic category (e.g., Oncology, Cardiology, Endocrinology)
5. **Key Terms**: Other important search terms (drug names, mechanisms, population characteristics)

Return ONLY a JSON object with this exact structure:
{{
  "indication": "specific disease name" or null,
  "phase": "phase number in Roman numerals" or null,
  "status": "status term" or null,
  "therapeutic_area": "therapeutic area" or null,
  "key_terms": ["term1", "term2"] or []
}}

Examples:
- "phase 3 type 2 diabetes trials" -> {{"indication": "Type 2 Diabetes", "phase": "III", "status": null, "therapeutic_area": "Endocrinology", "key_terms": []}}
- "active NSCLC immunotherapy studies" -> {{"indication": "Non-Small Cell Lung Cancer", "phase": null, "status": "active", "therapeutic_area": "Oncology", "key_terms": ["immunotherapy"]}}
- "heart failure phase 2" -> {{"indication": "Heart Failure", "phase": "II", "status": null, "therapeutic_area": "Cardiology", "key_terms": []}}

Be precise and use medical terminology. Return ONLY the JSON, no explanation."""

    try:
        response = await llm_agent.generate_response(
            prompt,
            system_prompt="You are a clinical trial search expert. Extract structured criteria from natural language queries."
        )
        
        # Parse the JSON response
        import json
        # Clean the response to get just the JSON
        response = response.strip()
        if response.startswith('```json'):
            response = response[7:]
        if response.startswith('```'):
            response = response[3:]
        if response.endswith('```'):
            response = response[:-3]
        response = response.strip()
        
        criteria = json.loads(response)
        
        print(f"🤖 LLM analyzed query: {criteria}")
        return criteria
    except Exception as e:
        print(f"⚠️ LLM analysis failed: {e}, falling back to keyword search")
        # Fallback to simple keyword extraction
        return {
            "indication": None,
            "phase": None,
            "status": None,
            "therapeutic_area": None,
            "key_terms": query.lower().split()
        }

async def smart_search_trials(
    df: pd.DataFrame,
    query: str,
    use_llm: bool = True
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Perform smart search on trials using LLM-powered query understanding
    
    Args:
        df: DataFrame with trial data
        query: Natural language search query
        use_llm: Whether to use LLM for query analysis (default: True)
    
    Returns:
        Tuple of (filtered_df, search_metadata)
    """
    
    if use_llm:
        criteria = await analyze_search_query(query)
    else:
        criteria = {
            "indication": None,
            "phase": None,
            "status": None,
            "therapeutic_area": None,
            "key_terms": query.lower().split()
        }
    
    filtered_df = df.copy()
    filters_applied = []
    
    # Priority 1: Phase filter (most specific)
    if criteria.get("phase"):
        phase = criteria["phase"]
        print(f"  🎯 Filtering by Phase: {phase}")
        
        if 'Trial Phase' in filtered_df.columns:
            # Use word boundary to match exact phase
            phase_mask = filtered_df['Trial Phase'].astype(str).str.contains(
                f'\\b{phase}\\b', case=False, na=False, regex=True
            )
            filtered_df = filtered_df[phase_mask]
            filters_applied.append(f"Phase {phase}")
            print(f"     ✓ After phase filter: {len(filtered_df)} trials")
    
    # Priority 2: Indication/Disease filter (most important for relevance)
    if criteria.get("indication"):
        indication = criteria["indication"]
        print(f"  🎯 Filtering by Indication: {indication}")
        
        # Search in Disease and Therapeutic Area columns (NOT in criteria text)
        indication_mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        
        for col in ['Disease', 'Therapeutic Area', 'Trial Title', 'Patient Population', 'Trial Objective']:
            if col in filtered_df.columns:
                col_matches = filtered_df[col].astype(str).str.contains(
                    indication, case=False, na=False, regex=False
                )
                indication_mask = indication_mask | col_matches
        
        filtered_df = filtered_df[indication_mask]
        filters_applied.append(f"Indication: {indication}")
        print(f"     ✓ After indication filter: {len(filtered_df)} trials")
    
    # Priority 3: Therapeutic Area (broader category)
    if criteria.get("therapeutic_area") and not criteria.get("indication"):
        # Only apply if we don't have a specific indication
        therapeutic_area = criteria["therapeutic_area"]
        print(f"  🎯 Filtering by Therapeutic Area: {therapeutic_area}")
        
        if 'Therapeutic Area' in filtered_df.columns:
            area_mask = filtered_df['Therapeutic Area'].astype(str).str.contains(
                therapeutic_area, case=False, na=False, regex=False
            )
            filtered_df = filtered_df[area_mask]
            filters_applied.append(f"Therapeutic Area: {therapeutic_area}")
            print(f"     ✓ After therapeutic area filter: {len(filtered_df)} trials")
    
    # Priority 4: Status filter
    if criteria.get("status"):
        status = criteria["status"]
        print(f"  🎯 Filtering by Status: {status}")
        
        if 'Trial Status' in filtered_df.columns:
            # Map common terms
            status_map = {
                'active': 'Open',
                'recruiting': 'Open',
                'open': 'Open',
                'completed': 'Completed',
                'closed': 'Closed',
                'terminated': 'Terminated'
            }
            search_status = status_map.get(status.lower(), status)
            
            status_mask = filtered_df['Trial Status'].astype(str).str.contains(
                search_status, case=False, na=False, regex=False
            )
            filtered_df = filtered_df[status_mask]
            filters_applied.append(f"Status: {status}")
            print(f"     ✓ After status filter: {len(filtered_df)} trials")
    
    # Priority 5: Additional key terms (only search in relevant columns)
    if criteria.get("key_terms"):
        print(f"  🔍 Filtering by key terms: {criteria['key_terms']}")
        
        # Only search in these specific columns (NOT criteria text)
        relevant_columns = [
            'Trial Title',
            'Primary Tested Drug',
            'Other Tested Drug',
            'Primary_Tested_Drug_Mechanism_Of_Action',
            'Other_Tested_Drug_Mechanism_Of_Action',
            'Trial Objective'
        ]
        
        for term in criteria['key_terms']:
            if len(term) < 3:  # Skip very short terms
                continue
                
            term_mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
            
            for col in relevant_columns:
                if col in filtered_df.columns:
                    col_matches = filtered_df[col].astype(str).str.contains(
                        term, case=False, na=False, regex=False
                    )
                    term_mask = term_mask | col_matches
            
            if term_mask.any():
                filtered_df = filtered_df[term_mask]
                filters_applied.append(f"Keyword: {term}")
                print(f"     ✓ After '{term}' filter: {len(filtered_df)} trials")
    
    metadata = {
        "criteria": criteria,
        "filters_applied": filters_applied,
        "total_results": len(filtered_df)
    }
    
    return filtered_df, metadata









