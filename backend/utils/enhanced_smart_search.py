"""
Enhanced smart search utilities with full TrialTrove column awareness
Uses LLM to understand query intent and maps to appropriate columns for filtering
"""
from typing import List, Dict, Any, Tuple
import pandas as pd
from agents.llm_agent import llm_agent

# Comprehensive mapping of TrialTrove columns organized by category
TRIALTROVE_COLUMNS = {
    "core_identifiers": [
        "Trial ID", "Protocol/Trial ID", "Trial Title"
    ],
    "phase_status": [
        "Trial Phase", "Trial Status"
    ],
    "disease_therapeutic": [
        "Therapeutic Area", "Disease", "Patient Segment", "MeSH Term", "Trial ICD-10 Code"
    ],
    "sponsor": [
        "Sponsor/Collaborator", "Sponsor/Collaborator Role", "Sponsor/Collaborator Type",
        "Sponsor/Collaborator: Parent HQ Country"
    ],
    "drugs_primary": [
        "Primary Tested Drug", "Primary Tested Drug: Mechanism Of Action",
        "Primary Tested Drug: Target", "Primary Tested Drug: Therapeutic Class",
        "Primary Tested Drug: Drug Type"
    ],
    "drugs_other": [
        "Other Tested Drug", "Other Tested Drug: Mechanism Of Action",
        "Other Tested Drug: Target", "Other Tested Drug: Therapeutic Class"
    ],
    "biomarkers": [
        "Oncology Biomarker", "Oncology Biomarker Common Use(s)"
    ],
    "objectives_endpoints": [
        "Trial Objective", "Primary Endpoint", "Primary Endpoint Group", "Primary Endpoint Details",
        "Secondary/Other Endpoint", "Secondary/Other Endpoint Group", "Secondary/Other Endpoint Details"
    ],
    "timeline": [
        "Start Date", "Enrollment Duration (Mos.)", "Enrollment Close Date",
        "Treatment Duration (Mos.)", "Primary Completion Date", "Full Completion Date"
    ],
    "patient_population": [
        "Patient Population", "Inclusion Criteria", "Exclusion Criteria",
        "Patient Gender", "Patient Age Group", "Min Patient Age", "Max Patient Age"
    ],
    "enrollment": [
        "Target Accrual", "Actual Accrual (No. of patients)", "Pts/Site/Mo"
    ],
    "geography": [
        "Reported Sites", "Trial Region", "Countries", "Countries Count",
        "Site of Care", "HCP Specialty", "Physician Target", "No. of Physicians at Site"
    ],
    "treatment_design": [
        "Prior/Concurrent Therapy", "Treatment Plan", "Study Design", "Study Keywords"
    ],
    "results_outcomes": [
        "Trial Results", "Trial Outcomes", "Outcome Details", "Disposition of Patients"
    ]
}

# Flatten for easy lookup
ALL_COLUMNS = []
for category, columns in TRIALTROVE_COLUMNS.items():
    ALL_COLUMNS.extend(columns)

async def analyze_search_query_enhanced(query: str) -> Dict[str, Any]:
    """
    Use LLM to analyze the search query with full awareness of TrialTrove columns
    
    Returns:
        Dict with structured search criteria mapped to specific columns
    """
    
    # Build column context for LLM
    column_context = ""
    for category, columns in TRIALTROVE_COLUMNS.items():
        column_context += f"\n**{category.replace('_', ' ').title()}**: {', '.join(columns)}"
    
    prompt = f"""Analyze this clinical trial search query and extract structured search criteria.
You have access to the following TrialTrove database columns:
{column_context}

Query: "{query}"

Extract and map search criteria to the appropriate columns above. For each criterion:
1. Identify the search term or value
2. Map it to the MOST RELEVANT column(s) from the list above
3. Determine if it's an exact match, partial match, or fuzzy match

Return ONLY a JSON object with this structure:
{{
  "primary_filters": [
    {{
      "column": "exact column name from list above",
      "value": "search value",
      "match_type": "exact|partial|fuzzy",
      "priority": 1-5 (1=highest)
    }}
  ],
  "key_terms": ["additional", "search", "terms"],
  "query_interpretation": "brief description of what you understood"
}}

Examples:

Query: "phase 3 type 2 diabetes trials"
Output: {{
  "primary_filters": [
    {{"column": "Trial Phase", "value": "III", "match_type": "exact", "priority": 1}},
    {{"column": "Disease", "value": "Type 2 Diabetes", "match_type": "partial", "priority": 1}},
    {{"column": "Therapeutic Area", "value": "Endocrinology", "match_type": "partial", "priority": 2}}
  ],
  "key_terms": [],
  "query_interpretation": "Looking for Phase 3 clinical trials studying Type 2 Diabetes"
}}

Query: "NSCLC immunotherapy trials in China"
Output: {{
  "primary_filters": [
    {{"column": "Disease", "value": "Non-Small Cell Lung Cancer", "match_type": "partial", "priority": 1}},
    {{"column": "Therapeutic Area", "value": "Oncology", "match_type": "partial", "priority": 2}},
    {{"column": "Countries", "value": "China", "match_type": "partial", "priority": 1}},
    {{"column": "Primary Tested Drug: Mechanism Of Action", "value": "immunotherapy", "match_type": "fuzzy", "priority": 2}}
  ],
  "key_terms": ["immunotherapy"],
  "query_interpretation": "Looking for NSCLC trials using immunotherapy conducted in China"
}}

Query: "phase 3 diabetes trials that studied the chinese population"
Output: {{
  "primary_filters": [
    {{"column": "Trial Phase", "value": "III", "match_type": "exact", "priority": 1}},
    {{"column": "Disease", "value": "Diabetes", "match_type": "partial", "priority": 1}},
    {{"column": "Countries", "value": "China", "match_type": "partial", "priority": 1}},
    {{"column": "Patient Population", "value": "Chinese", "match_type": "fuzzy", "priority": 2}}
  ],
  "key_terms": [],
  "query_interpretation": "Looking for Phase 3 diabetes trials conducted in China or with Chinese patients"
}}

Query: "active recruiting heart failure trials sponsored by Pfizer"
Output: {{
  "primary_filters": [
    {{"column": "Trial Status", "value": "Open", "match_type": "partial", "priority": 1}},
    {{"column": "Disease", "value": "Heart Failure", "match_type": "partial", "priority": 1}},
    {{"column": "Sponsor/Collaborator", "value": "Pfizer", "match_type": "partial", "priority": 1}}
  ],
  "key_terms": ["recruiting", "active"],
  "query_interpretation": "Looking for actively recruiting heart failure trials with Pfizer as sponsor"
}}

Be precise with column names - they must EXACTLY match the names in the list above.
Consider all relevant columns for each search term.
Return ONLY the JSON, no explanation."""

    try:
        response = await llm_agent.generate_response(
            prompt,
            system_prompt="You are a clinical trial database expert with deep knowledge of TrialTrove schema. Map search queries to the most relevant database columns."
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
        
        print(f"🤖 Enhanced LLM analysis: {criteria.get('query_interpretation', 'N/A')}")
        print(f"   Mapped to {len(criteria.get('primary_filters', []))} filter(s)")
        for f in criteria.get('primary_filters', []):
            print(f"   - {f['column']}: {f['value']} ({f['match_type']}, priority={f['priority']})")
        
        return criteria
    except Exception as e:
        print(f"⚠️ Enhanced LLM analysis failed: {e}, falling back to simple analysis")
        # Fallback to simple keyword extraction
        return {
            "primary_filters": [],
            "key_terms": query.lower().split(),
            "query_interpretation": "Fallback to keyword search"
        }

async def enhanced_smart_search_trials(
    df: pd.DataFrame,
    query: str,
    use_llm: bool = True
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Perform smart search on trials with full TrialTrove column awareness
    
    Args:
        df: DataFrame with trial data
        query: Natural language search query
        use_llm: Whether to use LLM for query analysis (default: True)
    
    Returns:
        Tuple of (filtered_df, search_metadata)
    """
    
    print(f"🔍 Enhanced smart search for: '{query}'")
    print(f"   Starting with {len(df)} trials")
    
    if use_llm:
        criteria = await analyze_search_query_enhanced(query)
    else:
        criteria = {
            "primary_filters": [],
            "key_terms": query.lower().split(),
            "query_interpretation": "Keyword search (LLM disabled)"
        }
    
    filtered_df = df.copy()
    filters_applied = []
    
    # Apply primary filters in priority order
    primary_filters = criteria.get("primary_filters", [])
    primary_filters.sort(key=lambda x: x.get("priority", 999))
    
    for filter_spec in primary_filters:
        column = filter_spec.get("column")
        value = filter_spec.get("value")
        match_type = filter_spec.get("match_type", "partial")
        
        if not column or not value:
            continue
            
        # Check if column exists in dataframe
        if column not in filtered_df.columns:
            print(f"  ⚠️ Column '{column}' not found in data, skipping")
            continue
            
        print(f"  🎯 Applying filter: {column} = '{value}' ({match_type})")
        
        before_count = len(filtered_df)
        
        if match_type == "exact":
            # Exact match (case-insensitive)
            mask = filtered_df[column].astype(str).str.lower() == value.lower()
        elif match_type == "partial":
            # Partial match (substring, case-insensitive)
            mask = filtered_df[column].astype(str).str.contains(
                value, case=False, na=False, regex=False
            )
        else:  # fuzzy
            # Fuzzy match - try both word boundary and simple substring
            import re
            # First try word boundary match
            escaped_value = re.escape(value)
            mask = filtered_df[column].astype(str).str.contains(
                f'\\b{escaped_value}\\b', case=False, na=False, regex=True
            )
            # If word boundary returns nothing, fall back to partial match
            if not mask.any():
                print(f"     ⚠️ Word boundary match found nothing, trying partial match")
                mask = filtered_df[column].astype(str).str.contains(
                    value, case=False, na=False, regex=False
                )
        
        temp_filtered = filtered_df[mask]
        after_count = len(temp_filtered)
        
        # Only apply filter if it doesn't eliminate ALL results
        if after_count > 0:
            filtered_df = temp_filtered
            if after_count < before_count:
                filters_applied.append(f"{column}: {value}")
                print(f"     ✓ Filtered {before_count} → {after_count} trials")
            else:
                print(f"     ⚠️ No effect (still {after_count} trials)")
        else:
            print(f"     ⚠️ Filter would eliminate all results, skipping this filter")
            print(f"     → Keeping {before_count} trials from previous filters")
    
    # Apply additional key terms as broad search if we still have filters to apply
    key_terms = criteria.get("key_terms", [])
    if key_terms:
        print(f"  🔍 Applying key terms: {key_terms}")
        
        # Search across multiple relevant columns
        search_columns = [
            'Trial Title', 'Trial Objective', 'Primary Tested Drug', 
            'Other Tested Drug', 'Treatment Plan', 'Study Keywords'
        ]
        
        for term in key_terms:
            if len(term) < 3:  # Skip very short terms
                continue
                
            term_mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
            
            for col in search_columns:
                if col in filtered_df.columns:
                    col_matches = filtered_df[col].astype(str).str.contains(
                        term, case=False, na=False, regex=False
                    )
                    term_mask = term_mask | col_matches
            
            if term_mask.any():
                before_count = len(filtered_df)
                filtered_df = filtered_df[term_mask]
                after_count = len(filtered_df)
                filters_applied.append(f"Keyword: {term}")
                print(f"     ✓ '{term}' filtered {before_count} → {after_count} trials")
    
    metadata = {
        "query": query,
        "interpretation": criteria.get("query_interpretation", "N/A"),
        "filters_applied": filters_applied,
        "columns_searched": list(set([f.get("column") for f in primary_filters if f.get("column")])),
        "total_results": len(filtered_df)
    }
    
    print(f"📊 Enhanced search complete: {len(filtered_df)} matching trials")
    print(f"   Filters applied: {', '.join(filters_applied) if filters_applied else 'none'}")
    
    return filtered_df, metadata

