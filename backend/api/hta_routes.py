"""
HTA API Routes - Module 4: HTA & Market Access Intelligence
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import pandas as pd
from services.hta_intelligence_service import hta_intelligence_service
from services.comparator_service import comparator_service
from utils.optimized_data_loader import OptimizedDataLoader

router = APIRouter()


class HTAOutcomeRequest(BaseModel):
    """Request model for HTA outcome prediction"""
    asset_id: str
    market: str
    evidence_strength: float = 0.5
    comparator_clarity: float = 0.5
    precedent_strength: float = 0.5
    policy_environment: str = "moderate"


class RankComparatorsRequest(BaseModel):
    """Request model for ranking comparators"""
    asset_id: str
    comparators: List[Dict[str, Any]]
    indication: str
    market: str

def get_data_loader() -> OptimizedDataLoader:
    """Get data loader instance"""
    from utils.optimized_data_loader import OptimizedDataLoader
    return OptimizedDataLoader()


@router.get("/pathway/{asset_id}/{market}")
async def get_hta_pathway(asset_id: str, market: str):
    """Get HTA pathway timeline and requirements"""
    pathway = hta_intelligence_service.get_hta_pathway(asset_id, market)
    if not pathway:
        # Return default structure instead of None
        return {
            "asset_id": asset_id,
            "market": market,
            "pathway_steps": [],
            "timeline_months": None,
            "requirements": [],
            "message": "HTA pathway not calculated yet."
        }
    return pathway


@router.post("/outcome-likelihood")
async def predict_hta_outcome(request: HTAOutcomeRequest):
    """Predict HTA outcome likelihood"""
    result = hta_intelligence_service.predict_hta_outcome_likelihood(
        asset_id=request.asset_id,
        market=request.market,
        evidence_strength=request.evidence_strength,
        comparator_clarity=request.comparator_clarity,
        precedent_strength=request.precedent_strength,
        policy_environment=request.policy_environment
    )
    return result


@router.get("/comparators/{asset_id}")
async def get_comparator_recommendations(
    asset_id: str,
    indication: Optional[str] = None,
    market: Optional[str] = None,
    loader: OptimizedDataLoader = Depends(get_data_loader)
):
    """Get comparator recommendations for HTA"""
    # In real implementation, would get indication from asset
    if not indication:
        indication = "Unknown"
    if not market:
        market = "US"
    
    recommendations = comparator_service.recommend_comparators(
        asset_id=asset_id,
        indication=indication,
        market=market,
        loader=loader
    )
    return {"recommendations": recommendations}


@router.post("/comparators/rank")
async def rank_comparators(
    request: RankComparatorsRequest,
    loader: OptimizedDataLoader = Depends(get_data_loader)
):
    """Rank comparators by HTA likelihood"""
    ranked = hta_intelligence_service.rank_comparators(
        asset_id=request.asset_id,
        comparators=request.comparators,
        indication=request.indication,
        market=request.market,
        loader=loader
    )
    return {"ranked_comparators": ranked}


@router.get("/evidence-gaps/{asset_id}")
async def get_evidence_gaps(
    asset_id: str,
    market: str = Query(..., description="Market"),
    required_evidence: Optional[List[str]] = Query(None, description="Required evidence types"),
    available_evidence: Optional[List[str]] = Query(None, description="Available evidence types")
):
    """Get evidence gaps analysis"""
    # Default to empty lists if not provided
    required = required_evidence or []
    available = available_evidence or []
    
    gaps = hta_intelligence_service.analyze_evidence_gaps(
        asset_id=asset_id,
        market=market,
        required_evidence=required,
        available_evidence=available
    )
    return gaps


@router.get("/access-risk/{asset_id}/{market}")
async def calculate_access_risk(
    asset_id: str,
    market: str,
    endpoint_maturity: float = 0.5,
    comparator_clarity: float = 0.5,
    precedent_strength: float = 0.5,
    policy_uncertainty: float = 0.5,
    price_aggressiveness: float = 0.5
):
    """Calculate access risk score"""
    risk = hta_intelligence_service.calculate_access_risk(
        asset_id=asset_id,
        market=market,
        endpoint_maturity=endpoint_maturity,
        comparator_clarity=comparator_clarity,
        precedent_strength=precedent_strength,
        policy_uncertainty=policy_uncertainty,
        price_aggressiveness=price_aggressiveness
    )
    if not risk:
        # Return default structure
        return {
            "asset_id": asset_id,
            "market": market,
            "risk_score": None,
            "risk_level": "Unknown",
            "risk_factors": [],
            "message": "Access risk not calculated yet."
        }
    return risk


@router.get("/time-to-reimbursement")
async def predict_time_to_reimbursement(
    asset_id: str,
    market: str,
    evidence_completeness: float = 0.5,
    comparator_clarity: float = 0.5
):
    """Predict time-to-reimbursement"""
    timeline = hta_intelligence_service.predict_time_to_reimbursement(
        asset_id=asset_id,
        market=market,
        evidence_completeness=evidence_completeness,
        comparator_clarity=comparator_clarity
    )
    return timeline


@router.get("/precedents")
async def find_precedents(
    indication: str,
    market: str,
    loader: OptimizedDataLoader = Depends(get_data_loader)
):
    """Find similar HTA precedents"""
    # Use TrialTrove to find similar cases
    trial_df = loader.get_data('trialtrove')
    precedents = []
    
    if not trial_df.empty:
        # Safely access DataFrame columns
        disease_col = trial_df.get('Disease', pd.Series(dtype=str))
        if disease_col.empty:
            disease_col = trial_df.get('disease', pd.Series(dtype=str))
        
        if not disease_col.empty:
            matches = trial_df[
                disease_col.astype(str).str.contains(indication, case=False, na=False)
            ]
            
            for idx, row in matches.head(10).iterrows():
                precedents.append({
                    "drug": row.get('Primary Tested Drug') or row.get('drug_name', 'Unknown'),
                    "indication": indication,
                    "market": market,
                    "trial_id": row.get('Trial ID') or row.get('nct_id', ''),
                    "phase": row.get('Trial Phase') or row.get('phase', '')
                })
    
    return {"precedents": precedents}

