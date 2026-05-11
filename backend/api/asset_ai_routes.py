"""
Asset AI API Routes - Module 7: Agentic AI ("Talk to your Asset")
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from agents.asset_strategy_agent import asset_strategy_agent
from agents.llm_agent import llm_agent
from agents.fda_labels_agent import fda_labels_agent
from agents.fierce_pharma_agent import google_search_agent
from agents.trialtrove_agent import trialtrove_agent
from agents.pubmed_agent import pubmed_agent
from services.asset_management_service import asset_management_service
from utils.optimized_data_loader import OptimizedDataLoader
from utils.activity_logger import activity_logger, OperationType
from models.asset_strategy_models import (
    SubpopulationsResponse, IndicationsResponse, MoAResponse,
    ComparatorsResponse, BenefitHypothesisResponse, AssumptionSetResponse,
    PricingParametersResponse, TimelineRecommendationsResponse
)
import logging
import json
import re

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    asset_id: str
    query: str
    conversation_history: Optional[List[Dict[str, str]]] = None


class GenerationRequest(BaseModel):
    asset_id: str
    query: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    section_type: Optional[str] = None
    market: Optional[str] = None
    indication: Optional[str] = None
    therapeutic_area: Optional[str] = None
    current_value: Optional[str] = None


@router.post("/chat")
async def chat_with_asset(request: ChatRequest):
    """Chat with asset"""
    response = await asset_strategy_agent.chat_with_asset(
        asset_id=request.asset_id,
        query=request.query,
        conversation_history=request.conversation_history
    )
    return response


@router.post("/generate/overview")
async def generate_asset_overview(request: GenerationRequest):
    """Generate asset overview using FDA Labels, Google Search, and LLM"""
    try:
        asset = asset_management_service.get_asset(request.asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        # Gather data from graph backend agents
        data_sources = []
        
        # Search FDA Labels for the drug/indication
        drug_name = asset.asset_name.split('(')[0].strip() if '(' in asset.asset_name else asset.asset_name
        fda_query = f"{drug_name} {asset.indication or asset.therapeutic_area}"
        logger.info(f"🔍 Searching FDA Labels: {fda_query}")
        fda_results = await fda_labels_agent.search_labels(fda_query, max_results=10)
        if fda_results:
            data_sources.append(f"FDA Labels: Found {len(fda_results)} relevant labels")
            # Extract key info from FDA labels
            fda_context = "\n".join([
                f"- {r.get('drug_name', 'Unknown')}: {r.get('indication', 'N/A')} - {r.get('moa', 'N/A')}"
                for r in fda_results[:5]
            ])
        else:
            fda_context = "No FDA labels found"
        
        # Search web for recent information
        web_query = f"{drug_name} {asset.indication or asset.therapeutic_area} mechanism of action indications"
        print(f"🔍 Searching web: {web_query}")
        logger.info(f"🔍 Searching web: {web_query}")
        web_results = await google_search_agent.search_web(web_query, max_results=5)
        print(f"✅ Found {len(web_results) if web_results else 0} web results")
        web_context = ""
        if web_results:
            web_context = "\n".join([
                f"- {r.title}: {r.content[:200] if r.content else 'No content available'}"
                for r in web_results[:3]
            ])
        
        # Determine what to generate based on query
        query_lower = (request.query or '').lower()
        is_subpopulations_only = 'subpopulation' in query_lower
        is_indications_only = 'indication' in query_lower and 'subpopulation' not in query_lower
        is_moa_only = 'mechanism' in query_lower or 'moa' in query_lower
        
        # Build specific prompts with JSON schema requirements
        if is_subpopulations_only:
            prompt = f"""You are an expert pharmaceutical strategist. Generate patient subpopulations for this asset.

ASSET INFORMATION:
- Asset Name: {asset.asset_name}
- Therapeutic Area: {asset.therapeutic_area}
- Indication: {asset.indication or 'Not specified'}
- MoA: {asset.moa or 'Not specified'}

DATA SOURCES:
{fda_context}

RECENT INFORMATION:
{web_context}

Generate 3-5 relevant patient subpopulations for this asset based on the therapeutic area, indication, and mechanism of action.

Return ONLY valid JSON in this exact format:
{{
  "subpopulations": ["Subpopulation 1", "Subpopulation 2", "Subpopulation 3"]
}}

Each subpopulation should be a specific patient segment (e.g., "PD-L1 positive patients", "First-line treatment naive", "Elderly patients ≥75 years")."""
        elif is_indications_only:
            prompt = f"""You are an expert pharmaceutical strategist. Generate relevant indications for this asset.

ASSET INFORMATION:
- Asset Name: {asset.asset_name}
- Therapeutic Area: {asset.therapeutic_area}
- MoA: {asset.moa or 'Not specified'}

DATA SOURCES:
{fda_context}

RECENT INFORMATION:
{web_context}

Generate 3-5 relevant indications for this asset based on the therapeutic area and mechanism of action.

Return ONLY valid JSON in this exact format:
{{
  "indications": ["Indication 1", "Indication 2", "Indication 3"]
}}

Each indication should be a specific disease or condition (e.g., "Non-small cell lung cancer", "Metastatic melanoma")."""
        elif is_moa_only:
            prompt = f"""You are an expert pharmaceutical strategist. Generate a detailed mechanism of action for this asset.

ASSET INFORMATION:
- Asset Name: {asset.asset_name}
- Therapeutic Area: {asset.therapeutic_area}
- Indication: {asset.indication or 'Not specified'}

DATA SOURCES:
{fda_context}

RECENT INFORMATION:
{web_context}

Generate a detailed, specific mechanism of action description for this asset. Be concise but comprehensive (2-4 sentences).

Return ONLY valid JSON in this exact format:
{{
  "moa": "Detailed mechanism of action description here..."
}}"""
        else:
            prompt = f"""You are an expert pharmaceutical strategist. Generate comprehensive asset overview.

ASSET INFORMATION:
- Asset Name: {asset.asset_name}
- Therapeutic Area: {asset.therapeutic_area}
- Indication: {asset.indication or 'Not specified'}
- MoA: {asset.moa or 'Not specified'}
- Development Stage: {asset.development_stage or 'Not specified'}
- Status: {asset.status or 'Not specified'}

DATA SOURCES:
{fda_context}

RECENT INFORMATION:
{web_context}

USER REQUEST:
{request.query or 'Generate comprehensive asset overview including MoA, indications, and subpopulations'}

Return ONLY valid JSON in this exact format:
{{
  "moa": "Detailed mechanism of action description",
  "indications": ["Indication 1", "Indication 2", "Indication 3"],
  "subpopulations": ["Subpopulation 1", "Subpopulation 2", "Subpopulation 3"],
  "development_context": "Brief development context and timeline"
}}"""
        
        # Generate using structured LLM response
        system_prompt = "You are an expert pharmaceutical strategist. Always return valid JSON only, no markdown, no explanations."
        response_text = await llm_agent.generate_structured_response(prompt, system_prompt)
        
        # Parse JSON response
        try:
            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                parsed_data = json.loads(json_match.group())
            else:
                parsed_data = json.loads(response_text)
            
            # Return structured content
            if is_subpopulations_only:
                result = SubpopulationsResponse(**parsed_data)
                return {
                    "success": True,
                    "content": "\n".join([f"- {sub}" for sub in result.subpopulations]),
                    "subpopulations": result.subpopulations,
                    "sources": {
                        "fda_labels": len(fda_results) if fda_results else 0,
                        "web_search": len(web_results) if web_results else 0
                    }
                }
            elif is_indications_only:
                result = IndicationsResponse(**parsed_data)
                return {
                    "success": True,
                    "content": "\n".join([f"- {ind}" for ind in result.indications]),
                    "indications": result.indications,
                    "sources": {
                        "fda_labels": len(fda_results) if fda_results else 0,
                        "web_search": len(web_results) if web_results else 0
                    }
                }
            elif is_moa_only:
                result = MoAResponse(**parsed_data)
                return {
                    "success": True,
                    "content": result.moa,
                    "moa": result.moa,
                    "sources": {
                        "fda_labels": len(fda_results) if fda_results else 0,
                        "web_search": len(web_results) if web_results else 0
                    }
                }
            else:
                # Comprehensive overview
                return {
                    "success": True,
                    "content": f"**Mechanism of Action:**\n{parsed_data.get('moa', '')}\n\n**Indications:**\n" + "\n".join([f"- {ind}" for ind in parsed_data.get('indications', [])]) + f"\n\n**Subpopulations:**\n" + "\n".join([f"- {sub}" for sub in parsed_data.get('subpopulations', [])]) + f"\n\n**Development Context:**\n{parsed_data.get('development_context', '')}",
                    "moa": parsed_data.get('moa', ''),
                    "indications": parsed_data.get('indications', []),
                    "subpopulations": parsed_data.get('subpopulations', []),
                    "sources": {
                        "fda_labels": len(fda_results) if fda_results else 0,
                        "web_search": len(web_results) if web_results else 0
                    }
                }
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing structured response: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            # Fallback to plain text
            return {
                "success": True,
                "content": response_text,
                "sources": {
                    "fda_labels": len(fda_results) if fda_results else 0,
                    "web_search": len(web_results) if web_results else 0
                }
            }
    except Exception as e:
        logger.error(f"Error generating asset overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/assess-opportunity")
async def assess_opportunity(asset_id: str):
    """Generate early opportunity assessment"""
    # Use agent to synthesize assessment
    assessment = await asset_strategy_agent.chat_with_asset(
        asset_id=asset_id,
        query="Generate a comprehensive early opportunity assessment including key numbers, drivers, risks, and recommendations"
    )
    return assessment


@router.post("/tasks/recommend-comparators")
async def recommend_comparators(asset_id: str, indication: str, market: str):
    """Recommend comparators"""
    # Use agent tool
    result = await asset_strategy_agent._fetch_comparator_prices_tool(market, indication)
    return result


@router.post("/tasks/benchmark-pricing")
async def benchmark_pricing(asset_id: str, market: str):
    """Benchmark pricing"""
    result = await asset_strategy_agent._calculate_price_potential_tool(asset_id, market)
    return result


@router.post("/generate/assumption-set")
async def generate_assumption_set(request: GenerationRequest):
    """Generate assumption set using graph backend agents"""
    print(f"🚀 Starting assumption set generation for asset: {request.asset_id}")
    logger.info(f"🚀 Starting assumption set generation for asset: {request.asset_id}")
    try:
        asset = asset_management_service.get_asset(request.asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        print(f"📋 Asset found: {asset.asset_name}")
        
        # Gather data from multiple sources
        drug_name = asset.asset_name.split('(')[0].strip() if '(' in asset.asset_name else asset.asset_name
        
        # Search FDA Labels
        fda_query = f"{drug_name} {asset.indication or asset.therapeutic_area}"
        fda_results = await fda_labels_agent.search_labels(fda_query, max_results=10)
        fda_context = "\n".join([
            f"- {r.get('drug_name', 'Unknown')}: {r.get('indication', 'N/A')} - {r.get('moa', 'N/A')}"
            for r in fda_results[:5]
        ]) if fda_results else "No FDA labels found"
        
        # Search web for comparators
        web_query = f"{asset.indication or asset.therapeutic_area} treatment comparators standard of care"
        web_results = await google_search_agent.search_web(web_query, max_results=5)
        web_context = "\n".join([
            f"- {r.title}: {r.content[:200] if r.content else 'No content available'}"
            for r in web_results[:3]
        ]) if web_results else ""
        
        prompt = f"""You are an expert pharmaceutical strategist. Generate a comprehensive assumption set for this asset.

ASSET: {asset.asset_name}
Therapeutic Area: {asset.therapeutic_area}
Indication: {asset.indication or 'Not specified'}
MoA: {asset.moa or 'Not specified'}

FDA LABEL DATA:
{fda_context}

MARKET CONTEXT:
{web_context}

Generate a complete assumption set including:
1. Comparator set: 3-5 relevant comparators with drug name, indication, market, and rationale
2. Benefit hypothesis: Comprehensive markdown-formatted hypothesis with key differentiators and value proposition
3. Market assumptions: Key market dynamics and assumptions
4. Clinical assumptions: Key clinical assumptions

Return ONLY valid JSON in this exact format:
{{
  "comparators": [
    {{"drug": "Drug Name", "indication": "Indication", "market": "US", "rationale": "Why this comparator"}},
    {{"drug": "Drug Name 2", "indication": "Indication", "market": "US", "rationale": "Why this comparator"}}
  ],
  "benefit_hypothesis": "## Benefit Hypothesis\\n\\n### Primary Benefit Mechanism\\n...\\n\\n### Key Differentiators\\n...\\n\\n### Value Proposition\\n...",
  "key_differentiators": ["Differentiator 1", "Differentiator 2"],
  "value_proposition": "Clinical value proposition summary",
  "market_assumptions": {{
    "market_size": "Description",
    "growth_rate": "Description",
    "competitive_landscape": "Description"
  }},
  "clinical_assumptions": {{
    "efficacy_expectations": "Description",
    "safety_profile": "Description",
    "patient_selection": "Description"
  }}
}}"""
        
        system_prompt = "You are an expert pharmaceutical strategist. Always return valid JSON only, no markdown code blocks, no explanations."
        response_text = await llm_agent.generate_structured_response(prompt, system_prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                parsed_data = json.loads(json_match.group())
            else:
                parsed_data = json.loads(response_text)
            
            result = AssumptionSetResponse(**parsed_data)
            return {
                "success": True,
                "content": result.benefit_hypothesis,
                "updates": {
                    "comparators": result.comparators,
                    "benefit_hypothesis": result.benefit_hypothesis,
                    "market_assumptions": result.market_assumptions,
                    "clinical_assumptions": result.clinical_assumptions
                }
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing assumption set response: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            return {
                "success": True,
                "content": response_text,
                "updates": {}
            }
    except Exception as e:
        logger.error(f"Error generating assumption set: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/comparators")
async def generate_comparators(request: GenerationRequest):
    """Generate comparator recommendations using FDA Labels and web search"""
    print(f"🚀 Starting comparator generation for asset: {request.asset_id}")
    logger.info(f"🚀 Starting comparator generation for asset: {request.asset_id}")
    try:
        asset = asset_management_service.get_asset(request.asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        print(f"📋 Asset found: {asset.asset_name}")
        
        indication = request.indication or asset.indication or asset.therapeutic_area
        
        # Search FDA Labels for approved drugs in same indication
        fda_query = f"{indication} approved treatment"
        fda_results = await fda_labels_agent.search_labels(fda_query, max_results=20)
        
        # Search web for standard of care
        web_query = f"{indication} standard of care treatment guidelines"
        web_results = await google_search_agent.search_web(web_query, max_results=5)
        
        prompt = f"""You are an expert pharmaceutical strategist. Recommend relevant comparators for this asset.

Asset: {asset.asset_name}
Indication: {indication}
MoA: {asset.moa or 'Not specified'}

FDA APPROVED DRUGS IN INDICATION:
{chr(10).join([f"- {r.get('drug_name', 'Unknown')}: {r.get('indication', 'N/A')}" for r in fda_results[:10]]) if fda_results else 'None found'}

MARKET CONTEXT:
{chr(10).join([f"- {r.title}: {r.content[:150] if r.content else 'No content available'}" for r in web_results[:3]]) if web_results else 'None found'}

Recommend 3-5 relevant comparators. Each comparator should include:
- Drug name (brand or generic)
- Indication (same as asset indication)
- Market (e.g., "US", "EU")
- Rationale (brief explanation of why this is a relevant comparator)

Return ONLY valid JSON in this exact format:
{{
  "comparators": [
    {{"drug": "Drug Name", "indication": "{indication}", "market": "US", "rationale": "Why this comparator"}},
    {{"drug": "Drug Name 2", "indication": "{indication}", "market": "US", "rationale": "Why this comparator"}}
  ]
}}"""
        
        system_prompt = "You are an expert pharmaceutical strategist. Always return valid JSON only, no markdown, no explanations."
        response_text = await llm_agent.generate_structured_response(prompt, system_prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                parsed_data = json.loads(json_match.group())
            else:
                parsed_data = json.loads(response_text)
            
            result = ComparatorsResponse(**parsed_data)
            
            # Store comparators in comparator service
            from services.comparator_service import comparator_service
            comparator_service.store_comparators(request.asset_id, result.comparators)
            print(f"💾 Stored {len(result.comparators)} comparators for asset {request.asset_id}")
            
            return {
                "success": True,
                "content": "\n".join([f"- {c.get('drug', 'Unknown')}: {c.get('rationale', '')}" for c in result.comparators]),
                "comparators": result.comparators
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing comparators response: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            return {
                "success": True,
                "content": response_text,
                "comparators": []
            }
    except Exception as e:
        logger.error(f"Error generating comparators: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/benefit-hypothesis")
async def generate_benefit_hypothesis(request: GenerationRequest):
    """Generate benefit hypothesis using graph backend agents"""
    print(f"🚀 Starting benefit hypothesis generation for asset: {request.asset_id}")
    logger.info(f"🚀 Starting benefit hypothesis generation for asset: {request.asset_id}")
    try:
        asset = asset_management_service.get_asset(request.asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        print(f"📋 Asset found: {asset.asset_name}")
        
        # Gather data
        drug_name = asset.asset_name.split('(')[0].strip() if '(' in asset.asset_name else asset.asset_name
        fda_query = f"{drug_name} {asset.indication or asset.therapeutic_area}"
        fda_results = await fda_labels_agent.search_labels(fda_query, max_results=10)
        
        prompt = f"""You are an expert pharmaceutical strategist. Generate a comprehensive benefit hypothesis for this asset.

Asset: {asset.asset_name}
MoA: {asset.moa or 'Not specified'}
Indication: {asset.indication or 'Not specified'}

FDA LABEL DATA:
{chr(10).join([f"- {r.get('drug_name', 'Unknown')}: {r.get('indication', 'N/A')} - {r.get('moa', 'N/A')}" for r in fda_results[:5]]) if fda_results else 'None found'}

Generate a comprehensive benefit hypothesis in markdown format including:
1. Primary benefit mechanism (detailed explanation)
2. Key differentiators vs comparators (3-5 specific differentiators)
3. Clinical value proposition (clear value statement)
4. Unmet needs addressed (specific patient needs)

Return ONLY valid JSON in this exact format:
{{
  "benefit_hypothesis": "## Benefit Hypothesis\\n\\n### Primary Benefit Mechanism\\n[Detailed explanation]\\n\\n### Key Differentiators\\n- [Differentiator 1]\\n- [Differentiator 2]\\n\\n### Clinical Value Proposition\\n[Value statement]\\n\\n### Unmet Needs Addressed\\n[Specific needs]",
  "key_differentiators": ["Differentiator 1", "Differentiator 2", "Differentiator 3"],
  "value_proposition": "Clear value proposition summary"
}}"""
        
        system_prompt = "You are an expert pharmaceutical strategist. Always return valid JSON only, no markdown code blocks, no explanations."
        response_text = await llm_agent.generate_structured_response(prompt, system_prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                parsed_data = json.loads(json_match.group())
            else:
                parsed_data = json.loads(response_text)
            
            result = BenefitHypothesisResponse(**parsed_data)
            return {
                "success": True,
                "content": result.benefit_hypothesis
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing benefit hypothesis response: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            return {
                "success": True,
                "content": response_text
            }
    except Exception as e:
        logger.error(f"Error generating benefit hypothesis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/evidence-gaps")
async def analyze_evidence_gaps(request: GenerationRequest):
    """Analyze evidence gaps using graph backend agents"""
    print(f"🚀 Starting evidence gap analysis for asset: {request.asset_id}")
    logger.info(f"🚀 Starting evidence gap analysis for asset: {request.asset_id}")
    try:
        asset = asset_management_service.get_asset(request.asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        print(f"📋 Asset found: {asset.asset_name}")
        
        # Get existing evidence artifacts for this asset
        from services.evidence_artifact_service import evidence_artifact_service
        existing_artifacts = evidence_artifact_service.list_artifacts(asset_id=request.asset_id)
        print(f"📁 Found {len(existing_artifacts)} existing evidence artifacts")
        logger.info(f"📁 Found {len(existing_artifacts)} existing evidence artifacts")
        
        # Gather comprehensive evidence from multiple sources
        drug_name = asset.asset_name.split('(')[0].strip() if '(' in asset.asset_name else asset.asset_name
        indication = asset.indication or asset.therapeutic_area or ''
        
        # 1. Search web
        web_query = f"{drug_name} {indication} clinical trials evidence"
        print(f"🔍 Searching web: {web_query}")
        logger.info(f"🔍 Searching web: {web_query}")
        web_results = await google_search_agent.search_web(web_query, max_results=10)
        print(f"✅ Found {len(web_results) if web_results else 0} web results")
        
        # 2. Search TrialTrove
        search_query = f"{drug_name} {indication}".strip()
        print(f"🔍 Searching TrialTrove for: '{search_query}' (drug: {drug_name}, indication: {indication})")
        trial_results = []
        try:
            trial_results = await trialtrove_agent.search_studies(
                query=f"{drug_name} {indication}",
                max_results=10
            )
            print(f"✅ Found {len(trial_results) if trial_results else 0} trials")
        except Exception as e:
            print(f"⚠️ TrialTrove search error: {e}")
            logger.warning(f"TrialTrove search error: {e}")
        
        # 3. Search PubMed
        search_query = f"{drug_name} {indication}".strip()
        print(f"🔍 Searching PubMed for: '{search_query}' (drug: {drug_name}, indication: {indication})")
        pubmed_results = []
        try:
            pubmed_results = await pubmed_agent.search_publications(
                query=f"{drug_name} {indication}",
                max_results=10
            )
            print(f"✅ Found {len(pubmed_results) if pubmed_results else 0} publications")
        except Exception as e:
            print(f"⚠️ PubMed search error: {e}")
            logger.warning(f"PubMed search error: {e}")
        
        # 4. Search FDA Labels
        search_query = f"{drug_name} {indication}".strip()
        print(f"🔍 Searching FDA Labels for: '{search_query}' (drug: {drug_name}, indication: {indication})")
        fda_results = []
        try:
            fda_results = await fda_labels_agent.search_labels(
                query=f"{drug_name} {indication}",
                max_results=5
            )
            print(f"✅ Found {len(fda_results) if fda_results else 0} FDA labels")
        except Exception as e:
            print(f"⚠️ FDA Labels search error: {e}")
            logger.warning(f"FDA Labels search error: {e}")
        
        # 5. Gather pricing data (CPP Drug Costs and SPU)
        pricing_data = []
        try:
            from main_complete import data_loader as main_data_loader
            data_loader = main_data_loader
        except:
            from utils.optimized_data_loader import OptimizedDataLoader
            data_loader = OptimizedDataLoader()
        
        # Search CPP Drug Costs (for comparator pricing)
        try:
            drug_costs_df = data_loader.get_cpp_data('drug_costs')
            if not drug_costs_df.empty:
                # Search for drugs matching indication or drug name
                for col in drug_costs_df.columns:
                    if 'drug' in col.lower() or 'name' in col.lower():
                        matches = drug_costs_df[drug_costs_df[col].str.contains(drug_name, case=False, na=False)]
                        if not matches.empty:
                            pricing_data.extend([
                                {
                                    "type": "cpp_drug_cost",
                                    "drug": row.get(col, ""),
                                    "data": row.to_dict(),
                                    "source": "cpp_drug_costs"
                                }
                                for _, row in matches.head(5).iterrows()
                            ])
                            break
        except Exception as e:
            logger.warning(f"CPP Drug Costs search error: {e}")
        
        # Search CPP SPU (for pricing benchmarks)
        try:
            spu_df = data_loader.get_cpp_data('spu')
            if not spu_df.empty:
                # Get sample SPU data (country-specific pricing)
                for _, row in spu_df.head(5).iterrows():
                    row_dict = row.to_dict()
                    standard_cols = ['CPT_CODE', 'LONG_DESC', 'SHORT_DESC', 'PROCEDURE_LEVEL', 'PROC_GROUP']
                    country_cols = [col for col in spu_df.columns if col not in standard_cols]
                    
                    # Find all countries with valid prices
                    countries_with_prices = []
                    for col in country_cols:
                        try:
                            price_val = row_dict.get(col)
                            if price_val and (isinstance(price_val, (int, float)) and price_val > 0):
                                countries_with_prices.append((col, float(price_val)))
                        except:
                            continue
                    
                    # Prefer US, then EU countries, then others
                    if countries_with_prices:
                        preferred_countries = ['US', 'USA', 'GB', 'GBR', 'UK', 'DE', 'DEU', 'FR', 'FRA', 'CA', 'CAN', 'AU', 'AUS', 'JP', 'JPN']
                        country_found = None
                        price_found = None
                        
                        # Try to find a preferred country first
                        for pref_country in preferred_countries:
                            for country, price in countries_with_prices:
                                if pref_country in country.upper() or country.upper() in pref_country:
                                    country_found = country
                                    price_found = price
                                    break
                            if country_found:
                                break
                        
                        # If no preferred country, use the first one
                        if not country_found:
                            country_found, price_found = countries_with_prices[0]
                        
                        if country_found:
                            pricing_data.append({
                                "type": "cpp_spu",
                                "country": country_found,
                                "procedure_code": str(row_dict.get('CPT_CODE', '')),
                                "procedure_desc": str(row_dict.get('LONG_DESC', row_dict.get('SHORT_DESC', ''))),
                                "price": price_found,
                                "data": row_dict,
                                "source": "cpp_spu"
                            })
        except Exception as e:
            logger.warning(f"CPP SPU search error: {e}")
        
        # Format evidence for prompt
        evidence_sections = []
        
        # Include existing evidence artifacts FIRST (most important - what we already have)
        if existing_artifacts:
            evidence_sections.append("EXISTING EVIDENCE ARTIFACTS (Already uploaded/added):")
            for i, artifact in enumerate(existing_artifacts[:10], 1):  # Limit to 10 most recent
                # Handle artifact_type (could be enum or string)
                artifact_type = artifact.artifact_type
                if hasattr(artifact_type, 'value'):
                    artifact_type_str = artifact_type.value
                elif isinstance(artifact_type, str):
                    artifact_type_str = artifact_type
                else:
                    artifact_type_str = str(artifact_type)
                
                # Use artifact title prominently - this is what should be referenced in the analysis
                artifact_title = artifact.file_name or f"Artifact {i}"
                evidence_sections.append(f"  Artifact '{artifact_title}' (Type: {artifact_type_str})")
                
                # Extract key information from artifact
                if artifact.extracted_entities:
                    entities = artifact.extracted_entities
                    # Check if metadata is directly in entities or nested
                    metadata = entities.get('metadata', {}) if isinstance(entities.get('metadata'), dict) else {}
                    
                    # Also check if entities itself has the metadata fields
                    if not metadata:
                        metadata = {k: v for k, v in entities.items() if k != 'source_id' and k != 'metadata'}
                    
                    # Extract key information from metadata
                    if metadata.get('title') or entities.get('title'):
                        evidence_sections.append(f"     Title: {metadata.get('title') or entities.get('title')}")
                    if metadata.get('nct_id') or entities.get('nct_id'):
                        evidence_sections.append(f"     NCT ID: {metadata.get('nct_id') or entities.get('nct_id')}")
                    if metadata.get('pmid') or entities.get('pmid'):
                        evidence_sections.append(f"     PMID: {metadata.get('pmid') or entities.get('pmid')}")
                    if metadata.get('drug') or entities.get('drug'):
                        evidence_sections.append(f"     Drug: {metadata.get('drug') or entities.get('drug')}")
                    if metadata.get('indication') or entities.get('indication'):
                        evidence_sections.append(f"     Indication: {metadata.get('indication') or entities.get('indication')}")
                    
                    # Show extracted entities summary
                    if entities.get('source_id'):
                        evidence_sections.append(f"     Source ID: {entities.get('source_id')}")
                
                if artifact.linked_fields:
                    linked = artifact.linked_fields
                    if linked:
                        evidence_sections.append(f"     Linked to: {', '.join(linked.keys())}")
                if artifact.uploaded_at:
                    evidence_sections.append(f"     Uploaded: {artifact.uploaded_at[:10]}")
        else:
            evidence_sections.append("EXISTING EVIDENCE ARTIFACTS:")
            evidence_sections.append("  No evidence artifacts have been uploaded yet.")
        
        if web_results:
            evidence_sections.append("WEB SEARCH RESULTS:")
            for i, r in enumerate(web_results[:5], 1):
                evidence_sections.append(f"  {i}. {r.title}")
                if r.content:
                    evidence_sections.append(f"     Content: {r.content[:300]}")
                if r.url:
                    evidence_sections.append(f"     URL: {r.url}")
        
        if trial_results:
            evidence_sections.append("\nCLINICAL TRIALS (TrialTrove):")
            for i, t in enumerate(trial_results[:5], 1):
                trial_title = getattr(t, 'title', getattr(t, 'official_title', 'Unknown Trial'))
                trial_id = getattr(t, 'nct_id', getattr(t, 'trial_id', ''))
                phase = getattr(t, 'phase', getattr(t, 'trial_phase', ''))
                evidence_sections.append(f"  {i}. {trial_title}")
                if trial_id:
                    evidence_sections.append(f"     NCT ID: {trial_id}")
                if phase:
                    evidence_sections.append(f"     Phase: {phase}")
        
        if pubmed_results:
            evidence_sections.append("\nPUBLICATIONS (PubMed):")
            for i, p in enumerate(pubmed_results[:5], 1):
                title = getattr(p, 'title', 'Unknown Publication')
                pmid = getattr(p, 'pmid', '')
                abstract = getattr(p, 'abstract', '')[:200] if hasattr(p, 'abstract') else ''
                evidence_sections.append(f"  {i}. {title}")
                if pmid:
                    evidence_sections.append(f"     PMID: {pmid}")
                if abstract:
                    evidence_sections.append(f"     Abstract: {abstract}")
        
        if fda_results:
            evidence_sections.append("\nFDA LABELS:")
            for i, f in enumerate(fda_results[:3], 1):
                drug_name_fda = getattr(f, 'drug_name', getattr(f, 'product_name', 'Unknown Drug'))
                indication_fda = getattr(f, 'indication', '')
                evidence_sections.append(f"  {i}. {drug_name_fda}")
                if indication_fda:
                    evidence_sections.append(f"     Indication: {indication_fda}")
        
        if pricing_data:
            evidence_sections.append("\nPRICING DATA:")
            drug_cost_count = 0
            spu_count = 0
            for price in pricing_data[:10]:
                if price.get('type') == 'cpp_drug_cost':
                    drug_cost_count += 1
                    drug_name_price = price.get('drug', 'Unknown Drug')
                    price_data = price.get('data', {})
                    # Extract relevant pricing fields
                    price_fields = []
                    for key in ['Price', 'Cost', 'WAC', 'AWP', 'List Price']:
                        if key in price_data and price_data[key]:
                            price_fields.append(f"{key}: {price_data[key]}")
                    evidence_sections.append(f"  Drug Cost {drug_cost_count}. {drug_name_price}")
                    if price_fields:
                        evidence_sections.append(f"     Pricing: {', '.join(price_fields)}")
                elif price.get('type') == 'cpp_spu':
                    spu_count += 1
                    country = price.get('country', 'Unknown')
                    procedure = price.get('procedure_desc', price.get('procedure_code', 'Unknown'))
                    price_val = price.get('price', 0)
                    evidence_sections.append(f"  SPU {spu_count}. {procedure} ({country})")
                    if price_val:
                        evidence_sections.append(f"     Price: ${price_val:,.2f}")
        
        evidence_text = "\n".join(evidence_sections) if evidence_sections else "Limited evidence found"
        
        print(f"📊 Compiling evidence gap analysis with {len(existing_artifacts)} artifacts and external sources")
        logger.info(f"📊 Compiling evidence gap analysis with {len(existing_artifacts)} artifacts and external sources")
        
        prompt = f"""You are an expert pharmaceutical strategist. Analyze evidence gaps for this asset.

Asset: {asset.asset_name}
Indication: {indication or 'Not specified'}
Development Stage: {asset.development_stage or 'Not specified'}
Therapeutic Area: {asset.therapeutic_area or 'Not specified'}

AVAILABLE EVIDENCE:
{evidence_text}

CRITICAL REQUIREMENT: For EVERY gap, recommendation, and required study, you MUST:
1. **Consider existing evidence artifacts FIRST** - Review what evidence has already been uploaded/added to identify what's missing
2. Provide a clear rationale explaining WHY it's needed
3. Cite SPECIFIC evidence that drives this conclusion - **ALWAYS use the artifact TITLE (file_name) when referencing existing evidence artifacts, NOT numbers**. For example, use "artifact 'Protocol Document v2.1.pdf'" instead of "artifact #1"
4. Explain what specific data or evidence is missing that creates this gap
5. **PRICING IMPLICATIONS**: If pricing data is available, analyze whether the evidence supports a higher price point. Note:
   - If clinical evidence shows superior efficacy, safety, or patient outcomes compared to comparators, this may support premium pricing
   - If pricing data shows comparator drugs are priced higher, this may indicate market willingness to pay
   - If evidence gaps exist that could limit pricing power, identify these specifically
   - Include pricing-related recommendations in the recommendations section

IMPORTANT: When identifying gaps, consider:
- What evidence artifacts already exist (listed in "EXISTING EVIDENCE ARTIFACTS" section)
- What additional evidence is available from external sources (web, trials, publications, FDA labels)
- What is STILL MISSING despite existing artifacts and external sources
- Focus on gaps that are NOT already covered by existing evidence artifacts

Analyze and identify:
1. Key evidence gaps (critical missing data) - with rationale and evidence citations, considering what already exists
2. Required studies/data (what needs to be generated) - with rationale pointing to what evidence shows this is needed, excluding what's already in artifacts
3. Priority areas (tier 1-3 priorities) - with rationale for why each is prioritized, accounting for existing evidence
4. Risk assessment (high/medium/low risk areas) - with rationale based on available evidence and existing artifacts
5. **Pricing implications** - analyze if available evidence supports premium pricing or identifies pricing risks

Return ONLY valid JSON in this exact format:
{{
  "evidence_gaps": [
    {{
      "gap": "Description of gap",
      "priority": "High/Medium/Low",
      "impact": "Impact description",
      "rationale": "Why this gap exists - cite specific evidence (e.g., 'Web result #2 shows X but lacks Y')",
      "evidence_references": ["Reference to specific evidence that shows this gap", "e.g., 'TrialTrove trial #3 lacks OS data'"]
    }}
  ],
  "required_studies": [
    {{
      "study_type": "Type of study",
      "rationale": "Why needed - cite specific evidence that demonstrates this need (e.g., 'PubMed #1 shows efficacy but lacks safety data')",
      "timeline": "Expected timeline",
      "evidence_references": ["Specific evidence that drives this requirement"]
    }}
  ],
  "priority_areas": {{
    "tier_1": [
      {{
        "area": "Critical priority 1",
        "rationale": "Why this is critical - cite evidence",
        "evidence_references": ["Evidence that shows this is critical"]
      }}
    ],
    "tier_2": [
      {{
        "area": "High priority 1",
        "rationale": "Why this is high priority - cite evidence",
        "evidence_references": ["Evidence that shows this priority"]
      }}
    ],
    "tier_3": [
      {{
        "area": "Important priority 1",
        "rationale": "Why this is important - cite evidence",
        "evidence_references": ["Evidence that shows this importance"]
      }}
    ]
  }},
  "risk_assessment": {{
    "regulatory_risk": {{
      "level": "High/Medium/Low",
      "explanation": "Detailed explanation with evidence citations",
      "evidence_references": ["Specific evidence that indicates this risk level"]
    }},
    "commercial_risk": {{
      "level": "High/Medium/Low",
      "explanation": "Detailed explanation with evidence citations",
      "evidence_references": ["Specific evidence that indicates this risk level"]
    }},
    "development_risk": {{
      "level": "High/Medium/Low",
      "explanation": "Detailed explanation with evidence citations",
      "evidence_references": ["Specific evidence that indicates this risk level"]
    }}
  }},
  "recommendations": [
    {{
      "recommendation": "Recommendation 1",
      "rationale": "Why this is recommended - cite specific evidence",
      "evidence_references": ["Evidence that supports this recommendation"]
    }}
  ],
  "pricing_insights": {{
    "supports_premium_pricing": true/false,
    "rationale": "Why evidence does/doesn't support premium pricing - cite specific evidence",
    "key_differentiators": ["Evidence-based differentiators that support pricing", "e.g., 'Superior OS data from Trial #2'"],
    "pricing_risks": ["Evidence gaps that could limit pricing power", "e.g., 'Lack of head-to-head comparator data'"],
    "evidence_references": ["Specific evidence that informs pricing assessment"]
  }}
}}"""
        
        system_prompt = "You are an expert pharmaceutical strategist. Always return valid JSON only, no markdown, no explanations. Every gap, study, priority, risk, and recommendation MUST include rationale with specific evidence citations."
        print(f"🤖 Generating evidence gap analysis with AI...")
        logger.info(f"🤖 Generating evidence gap analysis with AI...")
        response_text = await llm_agent.generate_structured_response(prompt, system_prompt)
        print(f"✅ AI response received, parsing...")
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                parsed_data = json.loads(json_match.group())
            else:
                parsed_data = json.loads(response_text)
            
            # Format as markdown for display with rationale and evidence references
            gaps_md = []
            for gap in parsed_data.get('evidence_gaps', []):
                gap_text = f"- **{gap.get('gap', '')}** (Priority: {gap.get('priority', 'Unknown')})"
                if gap.get('impact'):
                    gap_text += f" - {gap.get('impact')}"
                if gap.get('rationale'):
                    gap_text += f"\n  - *Rationale*: {gap.get('rationale')}"
                if gap.get('evidence_references'):
                    refs = gap.get('evidence_references', [])
                    gap_text += f"\n  - *Evidence*: {', '.join(refs)}"
                gaps_md.append(gap_text)
            
            studies_md = []
            for study in parsed_data.get('required_studies', []):
                study_text = f"- **{study.get('study_type', '')}** (Timeline: {study.get('timeline', 'TBD')})"
                if study.get('rationale'):
                    study_text += f"\n  - *Rationale*: {study.get('rationale')}"
                if study.get('evidence_references'):
                    refs = study.get('evidence_references', [])
                    study_text += f"\n  - *Evidence*: {', '.join(refs)}"
                studies_md.append(study_text)
            
            def format_priority_item(item):
                if isinstance(item, dict):
                    item_text = f"- {item.get('area', 'Unknown')}"
                    if item.get('rationale'):
                        item_text += f"\n  - *Rationale*: {item.get('rationale')}"
                    if item.get('evidence_references'):
                        refs = item.get('evidence_references', [])
                        item_text += f"\n  - *Evidence*: {', '.join(refs)}"
                    return item_text
                else:
                    return f"- {item}"
            
            tier1_md = [format_priority_item(item) for item in parsed_data.get('priority_areas', {}).get('tier_1', [])]
            tier2_md = [format_priority_item(item) for item in parsed_data.get('priority_areas', {}).get('tier_2', [])]
            tier3_md = [format_priority_item(item) for item in parsed_data.get('priority_areas', {}).get('tier_3', [])]
            
            risk_assessment = parsed_data.get('risk_assessment', {})
            reg_risk = risk_assessment.get('regulatory_risk', {})
            comm_risk = risk_assessment.get('commercial_risk', {})
            dev_risk = risk_assessment.get('development_risk', {})
            
            def format_risk(risk):
                if isinstance(risk, dict):
                    risk_text = f"**{risk.get('level', 'Unknown')}**"
                    if risk.get('explanation'):
                        risk_text += f": {risk.get('explanation')}"
                    if risk.get('evidence_references'):
                        refs = risk.get('evidence_references', [])
                        risk_text += f"\n  - *Evidence*: {', '.join(refs)}"
                    return risk_text
                else:
                    return str(risk)
            
            recs_md = []
            for rec in parsed_data.get('recommendations', []):
                if isinstance(rec, dict):
                    rec_text = f"- **{rec.get('recommendation', 'Unknown')}**"
                    if rec.get('rationale'):
                        rec_text += f"\n  - *Rationale*: {rec.get('rationale')}"
                    if rec.get('evidence_references'):
                        refs = rec.get('evidence_references', [])
                        rec_text += f"\n  - *Evidence*: {', '.join(refs)}"
                    recs_md.append(rec_text)
                else:
                    recs_md.append(f"- {rec}")
            
            # Format pricing insights
            pricing_insights = parsed_data.get('pricing_insights', {})
            pricing_md = []
            if pricing_insights:
                supports_premium = pricing_insights.get('supports_premium_pricing', False)
                pricing_md.append(f"- **Supports Premium Pricing**: {'Yes' if supports_premium else 'No'}")
                if pricing_insights.get('rationale'):
                    pricing_md.append(f"  - *Rationale*: {pricing_insights.get('rationale')}")
                if pricing_insights.get('key_differentiators'):
                    pricing_md.append(f"  - *Key Differentiators*:")
                    for diff in pricing_insights.get('key_differentiators', []):
                        pricing_md.append(f"    - {diff}")
                if pricing_insights.get('pricing_risks'):
                    pricing_md.append(f"  - *Pricing Risks*:")
                    for risk in pricing_insights.get('pricing_risks', []):
                        pricing_md.append(f"    - {risk}")
                if pricing_insights.get('evidence_references'):
                    refs = pricing_insights.get('evidence_references', [])
                    pricing_md.append(f"  - *Evidence*: {', '.join(refs)}")
            
            content = f"""# Evidence Gap Analysis: {asset.asset_name}

## Key Evidence Gaps

{chr(10).join(gaps_md) if gaps_md else 'No evidence gaps identified'}

## Required Studies/Data

{chr(10).join(studies_md) if studies_md else 'No required studies identified'}

## Priority Areas

### Tier 1 (Critical)
{chr(10).join(tier1_md) if tier1_md else 'No Tier 1 priorities identified'}

### Tier 2 (High Priority)
{chr(10).join(tier2_md) if tier2_md else 'No Tier 2 priorities identified'}

### Tier 3 (Important)
{chr(10).join(tier3_md) if tier3_md else 'No Tier 3 priorities identified'}

## Risk Assessment

- **Regulatory Risk**: {format_risk(reg_risk)}
- **Commercial Risk**: {format_risk(comm_risk)}
- **Development Risk**: {format_risk(dev_risk)}

## Recommendations

{chr(10).join(recs_md) if recs_md else 'No recommendations provided'}

## Pricing Implications

{chr(10).join(pricing_md) if pricing_md else 'No pricing insights available'}"""
            
            return {
                "success": True,
                "content": content,
                "structured_data": parsed_data
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing evidence gaps response: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            return {
                "success": True,
                "content": response_text
            }
    except Exception as e:
        logger.error(f"Error analyzing evidence gaps: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/price-potential")
async def generate_price_potential(request: GenerationRequest):
    """Generate price potential analysis using graph backend agents"""
    print(f"🚀 Starting price potential generation for asset: {request.asset_id}")
    logger.info(f"🚀 Starting price potential generation for asset: {request.asset_id}")
    operation_id = None
    try:
        asset = asset_management_service.get_asset(request.asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        print(f"📋 Asset found: {asset.asset_name}")
        
        # Start activity tracking
        operation_id = activity_logger.start_operation(
            operation_type=OperationType.PRICING_CALC,
            context={"asset_id": request.asset_id, "tab": "pricing"},
            metadata={"operation": "price_potential_generation", "asset_name": asset.asset_name}
        )
        
        market = request.market or "US"
        indication = request.indication or asset.indication or asset.therapeutic_area
        
        # Search for pricing information
        activity_logger.start_step(operation_id, "Searching pricing data", f"Gathering pricing information for {indication} in {market}")
        web_query = f"{indication} drug pricing market access {market}"
        web_results = await google_search_agent.search_web(web_query, max_results=5)
        activity_logger.complete_step(operation_id, "Searching pricing data", f"Found {len(web_results) if web_results else 0} pricing sources")
        activity_logger.update_progress(operation_id, 40.0, "Searching pricing data", f"Found {len(web_results) if web_results else 0} pricing sources")
        
        prompt = f"""You are an expert pharmaceutical pricing strategist. Generate price potential analysis for this asset.

Asset: {asset.asset_name}
Market: {market}
Indication: {indication}
MoA: {asset.moa or 'Not specified'}

MARKET CONTEXT:
{chr(10).join([f"- {r.title}: {r.content[:200] if r.content else 'No content available'}" for r in web_results[:3]]) if web_results else 'None found'}

Generate comprehensive price potential analysis including:
1. Price positioning strategy (premium/parity/discount)
2. Comparator pricing context (key comparator prices)
3. Value-based pricing rationale (why this price)
4. Market access considerations (payer requirements, HTA implications)

Return ONLY valid JSON in this exact format:
{{
  "price_positioning": "premium/parity/discount",
  "positioning_rationale": "Why this positioning",
  "comparator_pricing": [
    {{"drug": "Drug Name", "list_price": 100000, "net_price": 75000, "market": "{market}"}}
  ],
  "value_based_rationale": "Detailed rationale for value-based pricing",
  "market_access_considerations": "Key market access factors and requirements",
  "recommended_price_range": {{"min": 80000, "max": 120000}},
  "confidence": "High/Medium/Low"
}}"""
        
        system_prompt = "You are an expert pharmaceutical pricing strategist. Always return valid JSON only, no markdown, no explanations."
        activity_logger.start_step(operation_id, "Generating price potential", "Using AI to analyze pricing strategy")
        activity_logger.update_progress(operation_id, 70.0, "Generating price potential", "AI processing price potential analysis")
        response_text = await llm_agent.generate_structured_response(prompt, system_prompt)
        activity_logger.complete_step(operation_id, "Generating price potential", "AI price potential generation complete")
        activity_logger.update_progress(operation_id, 90.0, "Processing results", "Formatting price potential results")
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                parsed_data = json.loads(json_match.group())
            else:
                parsed_data = json.loads(response_text)
            
            # Format as markdown
            content = f"""# Price Potential Analysis: {asset.asset_name} ({market})

## Price Positioning Strategy

**Positioning**: {parsed_data.get('price_positioning', 'Unknown')}

**Rationale**: {parsed_data.get('positioning_rationale', '')}

## Comparator Pricing Context

{chr(10).join([f"- **{comp.get('drug', 'Unknown')}**: List ${comp.get('list_price', 0):,.0f}, Net ${comp.get('net_price', 0):,.0f}" for comp in parsed_data.get('comparator_pricing', [])])}

## Value-Based Pricing Rationale

{parsed_data.get('value_based_rationale', '')}

## Market Access Considerations

{parsed_data.get('market_access_considerations', '')}

## Recommended Price Range

${parsed_data.get('recommended_price_range', {}).get('min', 0):,.0f} - ${parsed_data.get('recommended_price_range', {}).get('max', 0):,.0f}

**Confidence**: {parsed_data.get('confidence', 'Unknown')}"""
            
            activity_logger.complete_operation(operation_id, {"price_potential_generated": True}, "Price potential analysis generated successfully")
            return {
                "success": True,
                "content": content,
                "structured_data": parsed_data
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing price potential response: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            activity_logger.error_operation(operation_id, f"Error parsing price potential response: {str(e)}")
            return {
                "success": True,
                "content": response_text
            }
    except Exception as e:
        logger.error(f"Error generating price potential: {e}", exc_info=True)
        if operation_id:
            activity_logger.error_operation(operation_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggest/pricing-parameters")
async def suggest_pricing_parameters(request: GenerationRequest):
    """Suggest pricing parameters using graph backend agents"""
    try:
        asset = asset_management_service.get_asset(request.asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        market = request.market or "US"
        indication = request.indication or asset.indication or asset.therapeutic_area
        
        # Search for comparator pricing
        web_query = f"{indication} drug prices {market} GoodRx"
        web_results = await google_search_agent.search_web(web_query, max_results=5)
        
        prompt = f"""You are an expert pharmaceutical pricing strategist. Suggest pricing parameters for this asset.

Asset: {asset.asset_name}
Market: {market}
Indication: {indication}
MoA: {asset.moa or 'Not specified'}

COMPARATOR PRICING:
{chr(10).join([f"- {r.title}: {r.content[:200] if r.content else 'No content available'}" for r in web_results[:3]]) if web_results else 'None found'}

Suggest pricing parameters based on:
1. Comparator pricing in the market
2. Asset's value proposition
3. Market access considerations
4. Standard rebate/discount ranges for the indication

Return ONLY valid JSON in this exact format:
{{
  "list_price_range": {{"min": 50000, "max": 100000}},
  "expected_rebate_pct": 25.5,
  "net_price_estimate": 75000,
  "pricing_strategy": "Value-based pricing strategy recommendations here...",
  "rationale": "Rationale for these pricing recommendations based on comparators and market context"
}}

All prices should be in USD. Rebate percentage should be 0-100."""
        
        system_prompt = "You are an expert pharmaceutical pricing strategist. Always return valid JSON only, no markdown, no explanations."
        response_text = await llm_agent.generate_structured_response(prompt, system_prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                parsed_data = json.loads(json_match.group())
            else:
                parsed_data = json.loads(response_text)
            
            result = PricingParametersResponse(**parsed_data)
            return {
                "success": True,
                "content": f"**List Price Range:** ${result.list_price_range.get('min', 0):,.0f} - ${result.list_price_range.get('max', 0):,.0f}\n\n**Expected Rebate:** {result.expected_rebate_pct}%\n\n**Net Price Estimate:** ${result.net_price_estimate:,.0f}\n\n**Pricing Strategy:**\n{result.pricing_strategy}\n\n**Rationale:**\n{result.rationale}",
                "pricing_parameters": {
                    "list_price_range": result.list_price_range,
                    "expected_rebate_pct": result.expected_rebate_pct,
                    "net_price_estimate": result.net_price_estimate,
                    "pricing_strategy": result.pricing_strategy,
                    "rationale": result.rationale
                }
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing pricing parameters response: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            return {
                "success": True,
                "content": response_text,
                "pricing_parameters": {}
            }
    except Exception as e:
        logger.error(f"Error suggesting pricing parameters: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/hta-assessment")
async def generate_hta_assessment(request: GenerationRequest):
    """Generate HTA assessment using graph backend agents"""
    try:
        asset = asset_management_service.get_asset(request.asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        market = request.market or "US"
        indication = request.indication or asset.indication or asset.therapeutic_area
        
        # Search for HTA/reimbursement information
        web_query = f"{indication} HTA reimbursement {market} NICE FDA"
        web_results = await google_search_agent.search_web(web_query, max_results=5)
        
        prompt = f"""You are an expert HTA and market access strategist. Generate HTA assessment for this asset.

Asset: {asset.asset_name}
Market: {market}
Indication: {indication}
MoA: {asset.moa or 'Not specified'}

HTA CONTEXT:
{chr(10).join([f"- {r.title}: {r.content[:200] if r.content else 'No content available'}" for r in web_results[:3]]) if web_results else 'None found'}

Generate comprehensive HTA assessment including:
1. HTA pathway overview (agency, process, timeline)
2. Evidence requirements (what evidence is needed)
3. Likely outcome assessment (approval probability)
4. Access risk factors (key risks)
5. Recommendations (actionable recommendations)

Return ONLY valid JSON in this exact format:
{{
  "hta_pathway": {{
    "agency": "HTA agency name",
    "process": "Description of HTA process",
    "timeline_months": 12,
    "key_milestones": ["Milestone 1", "Milestone 2"]
  }},
  "evidence_requirements": [
    {{"requirement": "Evidence type", "critical": true, "status": "Available/Missing"}}
  ],
  "outcome_assessment": {{
    "approval_probability": "High/Medium/Low",
    "rationale": "Why this probability",
    "key_factors": ["Factor 1", "Factor 2"]
  }},
  "access_risk_factors": [
    {{"risk": "Risk description", "severity": "High/Medium/Low", "mitigation": "Mitigation strategy"}}
  ],
  "recommendations": ["Recommendation 1", "Recommendation 2", "Recommendation 3"]
}}"""
        
        system_prompt = "You are an expert HTA and market access strategist. Always return valid JSON only, no markdown, no explanations."
        response_text = await llm_agent.generate_structured_response(prompt, system_prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                parsed_data = json.loads(json_match.group())
            else:
                parsed_data = json.loads(response_text)
            
            # Format as markdown
            pathway = parsed_data.get('hta_pathway', {})
            content = f"""# HTA Assessment: {asset.asset_name} ({market})

## HTA Pathway Overview

**Agency**: {pathway.get('agency', 'Unknown')}

**Process**: {pathway.get('process', '')}

**Timeline**: {pathway.get('timeline_months', 'Unknown')} months

**Key Milestones**:
{chr(10).join([f"- {milestone}" for milestone in pathway.get('key_milestones', [])])}

## Evidence Requirements

{chr(10).join([f"- **{req.get('requirement', '')}** ({'Critical' if req.get('critical') else 'Supporting'}): {req.get('status', 'Unknown')}" for req in parsed_data.get('evidence_requirements', [])])}

## Outcome Assessment

**Approval Probability**: {parsed_data.get('outcome_assessment', {}).get('approval_probability', 'Unknown')}

**Rationale**: {parsed_data.get('outcome_assessment', {}).get('rationale', '')}

**Key Factors**:
{chr(10).join([f"- {factor}" for factor in parsed_data.get('outcome_assessment', {}).get('key_factors', [])])}

## Access Risk Factors

{chr(10).join([f"- **{risk.get('risk', '')}** (Severity: {risk.get('severity', 'Unknown')}): {risk.get('mitigation', '')}" for risk in parsed_data.get('access_risk_factors', [])])}

## Recommendations

{chr(10).join([f"- {rec}" for rec in parsed_data.get('recommendations', [])])}"""
            
            return {
                "success": True,
                "content": content,
                "structured_data": parsed_data
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing HTA assessment response: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            return {
                "success": True,
                "content": response_text
            }
    except Exception as e:
        logger.error(f"Error generating HTA assessment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/generate-scenario-pack")
async def generate_scenario_pack(asset_id: str):
    """Generate scenario pack (base/upside/downside)"""
    # Use agent to generate scenarios
    scenarios = {
        "base": {"scenario_type": "base"},
        "upside": {"scenario_type": "upside"},
        "downside": {"scenario_type": "downside"}
    }
    return {"scenarios": scenarios}


@router.post("/generate/timeline")
async def generate_timeline_recommendations(request: GenerationRequest):
    """Generate comprehensive timeline recommendations using comparator-based analysis"""
    print(f"🚀 Starting timeline generation for asset: {request.asset_id}")
    logger.info(f"🚀 Starting timeline generation for asset: {request.asset_id}")
    operation_id = None
    try:
        asset = asset_management_service.get_asset(request.asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        print(f"📋 Asset found: {asset.asset_name}")
        
        # Start activity tracking
        operation_id = activity_logger.start_operation(
            operation_type=OperationType.AI_GENERATION,
            context={"asset_id": request.asset_id, "tab": "overview"},
            metadata={"operation": "timeline_generation", "asset_name": asset.asset_name}
        )
        
        # Gather data from multiple sources
        drug_name = asset.asset_name.split('(')[0].strip() if '(' in asset.asset_name else asset.asset_name
        indication = asset.indication or asset.therapeutic_area
        
        # Step 1: Find closest comparators
        activity_logger.start_step(operation_id, "Finding comparators", f"Searching FDA labels for comparators in {indication}")
        logger.info(f"🔍 Finding comparators for: {indication}")
        fda_query = f"{indication} approved treatment"
        fda_results = await fda_labels_agent.search_labels(fda_query, max_results=20)
        activity_logger.complete_step(operation_id, "Finding comparators", f"Found {len(fda_results) if fda_results else 0} comparators")
        activity_logger.update_progress(operation_id, 20.0, "Finding comparators", f"Found {len(fda_results) if fda_results else 0} comparators")
        
        # Step 2: Search for comparator launch timelines
        activity_logger.start_step(operation_id, "Searching comparator timelines", "Gathering launch timeline data for comparators")
        comparator_timelines = []
        if fda_results:
            for comp in fda_results[:5]:
                comp_drug = comp.get('drug_name', '')
                if comp_drug:
                    # Search for this comparator's approval/launch timeline
                    timeline_query = f"{comp_drug} {indication} FDA approval date launch timeline"
                    logger.info(f"🔍 Searching timeline for comparator: {comp_drug}")
                    comp_web_results = await google_search_agent.search_web(timeline_query, max_results=3)
                    if comp_web_results:
                        comparator_timelines.append({
                            'drug': comp_drug,
                            'indication': comp.get('indication', indication),
                            'timeline_info': "\n".join([
                                f"- {r.title}: {r.content[:300] if r.content else 'No content'}"
                                for r in comp_web_results[:2]
                            ])
                        })
        activity_logger.complete_step(operation_id, "Searching comparator timelines", f"Gathered timelines for {len(comparator_timelines)} comparators")
        activity_logger.update_progress(operation_id, 40.0, "Searching comparator timelines", f"Gathered timelines for {len(comparator_timelines)} comparators")
        
        # Step 3: Search for general historical submission timelines
        activity_logger.start_step(operation_id, "Searching historical timelines", "Gathering regulatory timeline data")
        web_query = f"{indication} FDA approval timeline submission milestones PDUFA date"
        logger.info(f"🔍 Searching for historical timelines: {web_query}")
        web_results = await google_search_agent.search_web(web_query, max_results=5)
        activity_logger.complete_step(operation_id, "Searching historical timelines", f"Found {len(web_results) if web_results else 0} timeline sources")
        activity_logger.update_progress(operation_id, 60.0, "Searching historical timelines", f"Found {len(web_results) if web_results else 0} timeline sources")
        
        # Step 4: Search TrialTrove for similar trials and their completion dates
        activity_logger.start_step(operation_id, "Searching TrialTrove", f"Finding similar trials in {indication}")
        trialtrove_query = f"{indication} {asset.therapeutic_area}"
        logger.info(f"🔍 Searching TrialTrove for similar trials: {trialtrove_query}")
        trialtrove_results = await trialtrove_agent.search_studies(trialtrove_query, max_results=10)
        activity_logger.complete_step(operation_id, "Searching TrialTrove", f"Found {len(trialtrove_results) if trialtrove_results else 0} similar trials")
        activity_logger.update_progress(operation_id, 70.0, "Searching TrialTrove", f"Found {len(trialtrove_results) if trialtrove_results else 0} similar trials")
        
        # Build comprehensive context
        historical_context = ""
        if comparator_timelines:
            historical_context += "COMPARATOR LAUNCH TIMELINES:\n"
            for comp in comparator_timelines:
                historical_context += f"\n{comp['drug']} ({comp['indication']}):\n{comp['timeline_info']}\n"
            historical_context += "\n"
        
        if web_results:
            historical_context += "REGULATORY TIMELINE INFORMATION:\n"
            historical_context += "\n".join([
                f"- {r.title}: {r.content[:300] if r.content else 'No content available'}"
                for r in web_results[:3]
            ]) + "\n\n"
        
        if trialtrove_results:
            historical_context += "SIMILAR TRIALS:\n"
            historical_context += "\n".join([
                f"- {r.title}: Phase {r.phase or 'Unknown'}, Status: {r.status or 'Unknown'}, Start: {r.start_date or 'Unknown'}, Completion: {r.completion_date or 'Unknown'}"
                for r in trialtrove_results[:5]
            ]) + "\n\n"
        
        if fda_results:
            historical_context += "FDA APPROVED DRUGS IN INDICATION:\n"
            historical_context += "\n".join([
                f"- {r.get('drug_name', 'Unknown')}: {r.get('indication', 'N/A')}"
                for r in fda_results[:5]
            ]) + "\n\n"
        
        # Calculate current date and typical timelines based on development stage
        from datetime import datetime, timedelta
        current_date = datetime.now()
        
        development_stage = asset.development_stage or 'phase_ii'
        
        # Determine which HIGH-LEVEL milestones are relevant based on current phase
        # Only include milestones that are relevant to current and future phases
        relevant_milestones = []
        
        # Phase III milestones - only if not yet in Phase III or currently in Phase III
        if development_stage in ['discovery', 'preclinical', 'phase_i', 'phase_ii']:
            relevant_milestones.append('Phase III Start')
        
        # Phase III completion and regulatory milestones - if in Phase III or earlier
        if development_stage in ['phase_ii', 'phase_iii', 'pre_launch']:
            relevant_milestones.append('Phase III Data Readout')
        
        # Regulatory submissions and approvals - if in Phase III or earlier (future milestones)
        if development_stage in ['discovery', 'preclinical', 'phase_i', 'phase_ii', 'phase_iii', 'pre_launch']:
            relevant_milestones.extend(['NDA Submission', 'FDA Approval', 'US Launch'])
            relevant_milestones.extend(['MAA Submission', 'EMA Approval', 'EU Launch'])
            relevant_milestones.extend(['NDA Submission (Japan)', 'PMDA Approval', 'JP Launch'])
        
        # Build dynamic JSON schema based on relevant milestones
        milestone_json_str = ',\n    '.join([f'"{m}": "YYYY-MM-DD"' for m in relevant_milestones]) if relevant_milestones else ''
        
        prompt = f"""You are an expert pharmaceutical regulatory strategist. Generate HIGH-LEVEL, phase-relative timeline recommendations for this asset using a comparator-based approach.

IMPORTANT: This is for the OVERVIEW section - only include KEY high-level milestones. Detailed regulatory milestones (pre-phase meetings, country-specific processes, CHMP day-by-day, etc.) belong in the HTA Timeline section, NOT here.

ASSET INFORMATION:
- Asset Name: {asset.asset_name}
- Therapeutic Area: {asset.therapeutic_area}
- Indication: {indication}
- Development Stage: {development_stage}
- MoA: {asset.moa or 'Not specified'}

CURRENT DATE: {current_date.strftime('%Y-%m-%d')}

HISTORICAL DATA FROM COMPARATORS:
{historical_context}

APPROACH:
1. Generate ONLY HIGH-LEVEL milestones RELATIVE to the current development stage ({development_stage})
2. Work BACKWARDS from expected launch dates to build milestone dates
3. Focus on major regulatory submissions and approvals only
4. DO NOT include pre-phase meetings, country-specific processes, or detailed regulatory steps

HIGH-LEVEL KEY MILESTONES - ONLY include what is RELEVANT to current phase ({development_stage}):

Based on current development stage ({development_stage}), ONLY include these milestones in your response:

{chr(10).join([f'- {m}' for m in relevant_milestones]) if relevant_milestones else '- No milestones relevant to current phase'}

CRITICAL: Only include the milestones listed above. DO NOT include:
- Milestones that are in the past (e.g., if in Phase III, don't include "Phase III Start")
- Milestones not listed above
- Any other milestones - only the ones listed above

TYPICAL TIMELINES (relative to current phase):
- Phase III duration: 24-36 months
- NDA preparation: 6-12 months after Phase III completion
- FDA review: 10-12 months (standard), 6-8 months (priority)
- EMA review: 12-18 months
- PMDA review: 12-18 months
- Launch preparation: 2-4 months after approval

KEY CONSIDERATIONS TO INCLUDE:
1. Therapeutic area may impact review timelines (oncology often faster)
2. Priority review designations can accelerate timelines
3. Orphan drug status may provide expedited pathways
4. Regulatory review timelines vary by agency

Based on the comparator timelines and historical data, calculate realistic dates working backwards from launch, ensuring all dates are relative to the current development stage ({development_stage}).

Return ONLY valid JSON in this exact format:
{{
  "expected_launch_dates": {{
    "US": "YYYY-MM-DD",
    "EU": "YYYY-MM-DD",
    "JP": "YYYY-MM-DD"
  }},
  "key_milestone_dates": {{
    {milestone_json_str if milestone_json_str else '// No milestones relevant to current phase'}
  }},
  "rationale": "Brief rationale explaining the timeline calculations",
  "historical_context": "Summary of comparator timelines used",
  "confidence": "High/Medium/Low",
  "considerations": "Detailed considerations including: (1) Competitor intelligence - how similar drugs made it to market, their submission strategies, timelines, and outcomes; (2) Regulatory precedents - similar drugs' approval pathways, review times, and any special designations; (3) Market access considerations - HTA requirements, pricing precedents, and reimbursement strategies for similar drugs; (4) Therapeutic area dynamics - competitive landscape, unmet needs, and market positioning opportunities; (5) Risk factors - regulatory, clinical, and commercial risks based on comparator experiences"
}}

CRITICAL: Only include milestones in "key_milestone_dates" that are listed in the "ONLY include these milestones" section above. 
- If a milestone is NOT listed above, DO NOT include it in the JSON response
- Only return the milestones that are relevant to the current phase ({development_stage})
- Do NOT return an empty object - if no milestones are relevant, return an empty "key_milestone_dates": {{}} object

CRITICAL REQUIREMENTS:
1. ONLY include milestones that are RELEVANT to the current development stage ({development_stage}) and future stages
2. ONLY include HIGH-LEVEL milestones (no pre-phase meetings, no country-specific processes, no detailed regulatory steps)
3. Launch dates MUST be populated for US, EU, JP at minimum
4. All milestone dates must be in chronological order
5. NDA Submission must be BEFORE FDA Approval (typically 10-12 months before)
6. Launch dates should be 2-4 months after respective approvals
7. Work backwards from launch dates to ensure logical sequence
8. DO NOT include detailed milestones - those belong in HTA Timeline section

All dates should be in YYYY-MM-DD format. Calculate dates based on current date ({current_date.strftime('%Y-%m-%d')}) and current development stage ({development_stage}). Only generate high-level milestones that are applicable given the current phase."""
        
        system_prompt = "You are an expert pharmaceutical regulatory strategist. Always return valid JSON only, no markdown, no explanations. Ensure all dates are in chronological order and launch dates are populated."
        activity_logger.start_step(operation_id, "Generating timeline recommendations", "Using AI to generate timeline recommendations based on gathered data")
        activity_logger.update_progress(operation_id, 80.0, "Generating timeline recommendations", "AI processing timeline recommendations")
        response_text = await llm_agent.generate_structured_response(prompt, system_prompt)
        activity_logger.complete_step(operation_id, "Generating timeline recommendations", "AI timeline generation complete")
        activity_logger.update_progress(operation_id, 90.0, "Validating dates", "Validating and processing timeline dates")
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                parsed_data = json.loads(json_match.group())
            else:
                parsed_data = json.loads(response_text)
            
            # Validate and fix date ordering
            from datetime import datetime as dt
            
            # Filter to only include milestones that are relevant to current phase
            # Use the same relevant_milestones list that was used in the prompt
            filtered_milestones = {}
            for milestone, date in parsed_data.get('key_milestone_dates', {}).items():
                # Only keep milestones that are in the relevant list for this phase
                if milestone in relevant_milestones:
                    filtered_milestones[milestone] = date
            parsed_data['key_milestone_dates'] = filtered_milestones
            
            # Ensure launch dates exist - always generate from milestone dates if not provided or empty
            expected_launch_dates = parsed_data.get('expected_launch_dates', {})
            if not expected_launch_dates or len(expected_launch_dates) == 0:
                # Generate launch dates from milestone dates
                us_approval = parsed_data.get('key_milestone_dates', {}).get('FDA Approval')
                eu_approval = parsed_data.get('key_milestone_dates', {}).get('EMA Approval')
                jp_approval = parsed_data.get('key_milestone_dates', {}).get('PMDA Approval')
                
                expected_launch_dates = {}
                if us_approval:
                    try:
                        approval_date = dt.strptime(us_approval, '%Y-%m-%d')
                        launch_date = (approval_date + timedelta(days=90)).strftime('%Y-%m-%d')
                        expected_launch_dates['US'] = launch_date
                    except:
                        pass
                if eu_approval:
                    try:
                        approval_date = dt.strptime(eu_approval, '%Y-%m-%d')
                        launch_date = (approval_date + timedelta(days=90)).strftime('%Y-%m-%d')
                        expected_launch_dates['EU'] = launch_date
                    except:
                        pass
                if jp_approval:
                    try:
                        approval_date = dt.strptime(jp_approval, '%Y-%m-%d')
                        launch_date = (approval_date + timedelta(days=90)).strftime('%Y-%m-%d')
                        expected_launch_dates['JP'] = launch_date
                    except:
                        pass
                
                # If still no launch dates, generate from US Launch milestone if available
                if len(expected_launch_dates) == 0:
                    us_launch = parsed_data.get('key_milestone_dates', {}).get('US Launch')
                    eu_launch = parsed_data.get('key_milestone_dates', {}).get('EU Launch')
                    jp_launch = parsed_data.get('key_milestone_dates', {}).get('JP Launch')
                    
                    if us_launch:
                        expected_launch_dates['US'] = us_launch
                    if eu_launch:
                        expected_launch_dates['EU'] = eu_launch
                    if jp_launch:
                        expected_launch_dates['JP'] = jp_launch
                
                parsed_data['expected_launch_dates'] = expected_launch_dates
            
            # Ensure NDA Submission is before FDA Approval
            milestones = parsed_data.get('key_milestone_dates', {})
            nda_submission = milestones.get('NDA Submission')
            fda_approval = milestones.get('FDA Approval')
            
            if nda_submission and fda_approval:
                try:
                    nda_date = dt.strptime(nda_submission, '%Y-%m-%d')
                    approval_date = dt.strptime(fda_approval, '%Y-%m-%d')
                    if nda_date >= approval_date:
                        # Fix: NDA should be 10 months before approval
                        new_nda_date = approval_date - timedelta(days=300)
                        parsed_data['key_milestone_dates']['NDA Submission'] = new_nda_date.strftime('%Y-%m-%d')
                except:
                    pass
            
            result = TimelineRecommendationsResponse(**parsed_data)
            # Return as dict for JSON serialization
            activity_logger.complete_operation(operation_id, {"timeline_generated": True}, "Timeline recommendations generated successfully")
            return result.model_dump()
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error parsing timeline recommendations response: {e}")
            logger.error(f"Response text: {response_text[:500]}")
            activity_logger.error_operation(operation_id, f"Error parsing timeline response: {str(e)}")
            return {
                "success": True,
                "expected_launch_dates": {},
                "key_milestone_dates": {},
                "rationale": response_text,
                "historical_context": "",
                "confidence": "Low",
                "considerations": "Unable to generate detailed considerations due to parsing error."
            }
    except Exception as e:
        logger.error(f"Error generating timeline recommendations: {e}", exc_info=True)
        if operation_id:
            activity_logger.error_operation(operation_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/discover/evidence")
async def discover_evidence(request: GenerationRequest):
    """Discover evidence for asset using ALL available data sources"""
    operation_id = None
    try:
        asset = asset_management_service.get_asset(request.asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail="Asset not found")
        
        # Start activity tracking
        operation_id = activity_logger.start_operation(
            operation_type=OperationType.EVIDENCE_DISCOVERY,
            context={"asset_id": request.asset_id, "tab": "evidence"},
            metadata={"operation": "evidence_discovery", "asset_name": asset.asset_name}
        )
        
        drug_name = asset.asset_name.split('(')[0].strip() if '(' in asset.asset_name else asset.asset_name
        indication = asset.indication or asset.therapeutic_area
        query = request.query or f"{drug_name} {indication}"
        
        # Initialize data loader once for all CPP/payer data searches
        try:
            from main_complete import data_loader as main_data_loader
            data_loader = main_data_loader
        except:
            from utils.optimized_data_loader import OptimizedDataLoader
            data_loader = OptimizedDataLoader()
        
        results = {
            "success": True,
            "trials": [],
            "publications": [],
            "web_results": [],
            "fda_labels": [],
            "comparators": [],
            "pricing_data": [],
            "country_specs": [],
            "indication_rules": [],
            "product_brands": [],
            "sites": []
        }
        
        # 1. Search TrialTrove
        activity_logger.start_step(operation_id, "Searching TrialTrove", f"Searching clinical trials: {query}")
        trial_query = query
        logger.info(f"🔍 Searching TrialTrove: {trial_query}")
        try:
            trial_results = await trialtrove_agent.search_studies(trial_query, max_results=20)
            results["trials"] = [t.dict() if hasattr(t, 'dict') else t for t in trial_results]
            logger.info(f"✅ Found {len(results['trials'])} trials")
            activity_logger.complete_step(operation_id, "Searching TrialTrove", f"Found {len(results['trials'])} trials")
        except Exception as e:
            logger.warning(f"TrialTrove search error: {e}")
            activity_logger.complete_step(operation_id, "Searching TrialTrove", f"Error: {str(e)}")
        activity_logger.update_progress(operation_id, 10.0, "Searching TrialTrove", f"Found {len(results['trials'])} trials")
        
        # 2. Search PubMed
        activity_logger.start_step(operation_id, "Searching PubMed", f"Searching publications: {query}")
        pubmed_query = query
        logger.info(f"🔍 Searching PubMed: {pubmed_query}")
        try:
            pubmed_results = await pubmed_agent.search_publications(pubmed_query, max_results=20)
            results["publications"] = [p.dict() if hasattr(p, 'dict') else p for p in pubmed_results]
            logger.info(f"✅ Found {len(results['publications'])} publications")
            activity_logger.complete_step(operation_id, "Searching PubMed", f"Found {len(results['publications'])} publications")
        except Exception as e:
            logger.warning(f"PubMed search error: {e}")
            activity_logger.complete_step(operation_id, "Searching PubMed", f"Error: {str(e)}")
        activity_logger.update_progress(operation_id, 20.0, "Searching PubMed", f"Found {len(results['publications'])} publications")
        
        # 3. Search web
        activity_logger.start_step(operation_id, "Searching web", f"Searching web for evidence: {query}")
        web_query = f"{query} clinical trial evidence"
        logger.info(f"🔍 Searching web: {web_query}")
        try:
            web_results = await google_search_agent.search_web(web_query, max_results=10)
            results["web_results"] = [r.dict() if hasattr(r, 'dict') else {"title": r.title, "url": r.url, "content": r.content[:500] if r.content else ""} for r in web_results]
            logger.info(f"✅ Found {len(results['web_results'])} web results")
            activity_logger.complete_step(operation_id, "Searching web", f"Found {len(results['web_results'])} web results")
        except Exception as e:
            logger.warning(f"Web search error: {e}")
            activity_logger.complete_step(operation_id, "Searching web", f"Error: {str(e)}")
        activity_logger.update_progress(operation_id, 30.0, "Searching web", f"Found {len(results['web_results'])} web results")
        
        # 4. Search FDA Labels
        activity_logger.start_step(operation_id, "Searching FDA Labels", f"Searching FDA labels: {drug_name} {indication}")
        fda_query = f"{drug_name} {indication}"
        logger.info(f"🔍 Searching FDA Labels: {fda_query}")
        try:
            fda_results = await fda_labels_agent.search_labels(fda_query, max_results=10)
            results["fda_labels"] = fda_results[:10]
            logger.info(f"✅ Found {len(results['fda_labels'])} FDA labels")
            activity_logger.complete_step(operation_id, "Searching FDA Labels", f"Found {len(results['fda_labels'])} FDA labels")
        except Exception as e:
            logger.warning(f"FDA Labels search error: {e}")
            activity_logger.complete_step(operation_id, "Searching FDA Labels", f"Error: {str(e)}")
        activity_logger.update_progress(operation_id, 40.0, "Searching FDA Labels", f"Found {len(results['fda_labels'])} FDA labels")
        
        # 5. Search CPP Drug Costs (for comparator pricing)
        activity_logger.start_step(operation_id, "Searching CPP Drug Costs", "Searching comparator pricing data")
        logger.info(f"🔍 Searching CPP Drug Costs for comparators")
        try:
            drug_costs_df = data_loader.get_cpp_data('drug_costs')
            if not drug_costs_df.empty:
                # Search for drugs matching indication or drug name
                for col in drug_costs_df.columns:
                    if 'drug' in col.lower() or 'name' in col.lower():
                        matches = drug_costs_df[drug_costs_df[col].str.contains(drug_name, case=False, na=False)]
                        if not matches.empty:
                            results["pricing_data"].extend([
                                {
                                    "type": "cpp_drug_cost",
                                    "drug": row.get(col, ""),
                                    "data": row.to_dict(),
                                    "source": "cpp_drug_costs"
                                }
                                for _, row in matches.head(5).iterrows()
                            ])
                            break
                logger.info(f"✅ Found {len(results['pricing_data'])} pricing records")
                activity_logger.complete_step(operation_id, "Searching CPP Drug Costs", f"Found {len(results['pricing_data'])} pricing records")
        except Exception as e:
            logger.warning(f"CPP Drug Costs search error: {e}")
            activity_logger.complete_step(operation_id, "Searching CPP Drug Costs", f"Error: {str(e)}")
        activity_logger.update_progress(operation_id, 50.0, "Searching CPP Drug Costs", f"Found {len(results['pricing_data'])} pricing records")
        
        # 6. Search CPP SPU (for pricing benchmarks)
        activity_logger.start_step(operation_id, "Searching CPP SPU", "Searching pricing benchmarks")
        logger.info(f"🔍 Searching CPP SPU for pricing benchmarks")
        try:
            spu_df = data_loader.get_cpp_data('spu')
            if not spu_df.empty:
                # Get sample SPU data (country-specific pricing)
                # SPU data has country codes as column names with price values
                spu_records = []
                for _, row in spu_df.head(5).iterrows():
                    row_dict = row.to_dict()
                    # Find country columns (columns that are not standard metadata columns and have numeric values)
                    standard_cols = ['CPT_CODE', 'LONG_DESC', 'SHORT_DESC', 'PROCEDURE_LEVEL', 'PROC_GROUP']
                    country_cols = [col for col in spu_df.columns if col not in standard_cols]
                    
                    # Find all countries with valid prices (not just the first one)
                    countries_with_prices = []
                    for col in country_cols:
                        try:
                            price_val = row_dict.get(col)
                            if price_val and (isinstance(price_val, (int, float)) and price_val > 0):
                                countries_with_prices.append((col, float(price_val)))
                        except:
                            continue
                    
                    # Create record for the first country with pricing (or best match)
                    if countries_with_prices:
                        # Prefer US, then EU countries, then others
                        preferred_countries = ['US', 'USA', 'GB', 'GBR', 'UK', 'DE', 'DEU', 'FR', 'FRA', 'CA', 'CAN', 'AU', 'AUS', 'JP', 'JPN']
                        country_found = None
                        price_found = None
                        
                        # Try to find a preferred country first
                        for pref_country in preferred_countries:
                            for country, price in countries_with_prices:
                                if pref_country in country.upper() or country.upper() in pref_country:
                                    country_found = country
                                    price_found = price
                                    break
                            if country_found:
                                break
                        
                        # If no preferred country, use the first one
                        if not country_found and countries_with_prices:
                            country_found, price_found = countries_with_prices[0]
                        
                        if country_found:
                            spu_records.append({
                                "type": "cpp_spu",
                                "country": country_found,
                                "procedure_code": str(row_dict.get('CPT_CODE', '')),
                                "procedure_desc": str(row_dict.get('LONG_DESC', row_dict.get('SHORT_DESC', ''))),
                                "price": price_found,
                                "data": row_dict,
                                "source": "cpp_spu"
                            })
                    # Only skip if truly no pricing data available
                
                results["pricing_data"].extend(spu_records)
                logger.info(f"✅ Found {len(spu_records)} SPU records")
                activity_logger.complete_step(operation_id, "Searching CPP SPU", f"Found {len(spu_records)} SPU records")
        except Exception as e:
            logger.warning(f"CPP SPU search error: {e}")
            activity_logger.complete_step(operation_id, "Searching CPP SPU", f"Error: {str(e)}")
        activity_logger.update_progress(operation_id, 60.0, "Searching CPP SPU", f"Found {len([r for r in results['pricing_data'] if r['type'] == 'cpp_spu'])} SPU records")
        
        # 7. Search Product Brands (for comparators)
        logger.info(f"🔍 Searching Product Brands for comparators")
        try:
            product_df = data_loader.get_product_brand_data()
            if not product_df.empty and indication:
                # Search for products matching indication or therapeutic area
                for col in product_df.columns:
                    if 'name' in col.lower() or 'product' in col.lower():
                        # Convert column to string if it's not already, and handle NaN values
                        try:
                            # Check if column is string type
                            if product_df[col].dtype == 'object':
                                # Convert to string, handling NaN
                                product_df[col] = product_df[col].astype(str).replace('nan', '')
                                matches = product_df[product_df[col].str.contains(indication, case=False, na=False)]
                            else:
                                # If not string, convert to string first
                                matches = product_df[product_df[col].astype(str).str.contains(indication, case=False, na=False)]
                            
                            if not matches.empty:
                                results["product_brands"] = [
                                    {
                                        "product_name": str(row.get(col, "")),
                                        "data": row.to_dict(),
                                        "source": "product_brand_dim"
                                    }
                                    for _, row in matches.head(10).iterrows()
                                ]
                                break
                        except Exception as col_error:
                            # Skip this column if it causes an error
                            logger.debug(f"Skipping column {col} due to error: {col_error}")
                            continue
                
                if "product_brands" in results:
                    logger.info(f"✅ Found {len(results['product_brands'])} product brands")
        except Exception as e:
            logger.warning(f"Product Brands search error: {e}")
        
        # 8. Search Country Specifications (for market-specific rules)
        logger.info(f"🔍 Searching Country Specifications")
        try:
            country_specs_df = data_loader.get_cpp_data('country_specs')
            if not country_specs_df.empty:
                results["country_specs"] = [
                    {
                        "country": row.get('Country', 'Unknown') if 'Country' in country_specs_df.columns else 'Unknown',
                        "data": row.to_dict(),
                        "source": "cpp_country_specs"
                    }
                    for _, row in country_specs_df.head(10).iterrows()
                ]
                logger.info(f"✅ Found {len(results['country_specs'])} country specifications")
        except Exception as e:
            logger.warning(f"Country Specs search error: {e}")
        
        # 9. Search Indication Rules
        logger.info(f"🔍 Searching Indication Rules")
        try:
            indications_df = data_loader.get_cpp_data('indications')
            if not indications_df.empty and indication:
                for col in indications_df.columns:
                    if 'indication' in col.lower() or 'disease' in col.lower():
                        matches = indications_df[indications_df[col].str.contains(indication, case=False, na=False)]
                        if not matches.empty:
                            results["indication_rules"] = [
                                {
                                    "indication": row.get(col, ""),
                                    "data": row.to_dict(),
                                    "source": "cpp_indications"
                                }
                                for _, row in matches.head(5).iterrows()
                            ]
                            break
                logger.info(f"✅ Found {len(results['indication_rules'])} indication rules")
        except Exception as e:
            logger.warning(f"Indication Rules search error: {e}")
        
        # 10. Search Sites (for site-related evidence)
        logger.info(f"🔍 Searching Sites")
        try:
            from agents.site_trove_agent import site_trove_agent
            site_results = await site_trove_agent.search_sites(query, max_results=10)
            results["sites"] = site_results[:10]
            logger.info(f"✅ Found {len(results['sites'])} sites")
        except Exception as e:
            logger.warning(f"Site search error: {e}")
        
        # 11. Get comparator recommendations
        activity_logger.start_step(operation_id, "Getting comparator recommendations", "Generating comparator recommendations")
        logger.info(f"🔍 Getting comparator recommendations")
        try:
            from services.comparator_service import comparator_service
            comparator_recs = comparator_service.recommend_comparators(
                asset_id=request.asset_id,
                indication=indication,
                market="US",
                therapeutic_area=asset.therapeutic_area,
                moa=asset.moa,
                loader=data_loader
            )
            results["comparators"] = comparator_recs[:10]
            logger.info(f"✅ Found {len(results['comparators'])} comparator recommendations")
            activity_logger.complete_step(operation_id, "Getting comparator recommendations", f"Found {len(results['comparators'])} comparator recommendations")
        except Exception as e:
            logger.warning(f"Comparator recommendation error: {e}")
            activity_logger.complete_step(operation_id, "Getting comparator recommendations", f"Error: {str(e)}")
        activity_logger.update_progress(operation_id, 95.0, "Finalizing results", "Compiling all evidence sources")
        
        total_results = sum([
            len(results.get("trials", [])),
            len(results.get("publications", [])),
            len(results.get("web_results", [])),
            len(results.get("fda_labels", [])),
            len(results.get("comparators", [])),
            len(results.get("pricing_data", [])),
            len(results.get("product_brands", []))
        ])
        activity_logger.complete_operation(operation_id, {"total_evidence_items": total_results}, f"Evidence discovery complete: {total_results} items found")
        return results
    except Exception as e:
        logger.error(f"Error discovering evidence: {e}", exc_info=True)
        if operation_id:
            activity_logger.error_operation(operation_id, str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/citations/{message_id}")
async def get_citations(message_id: str):
    """Get citations for a message"""
    # Placeholder
    return {"citations": []}

