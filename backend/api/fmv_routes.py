"""
Fair Market Value Analysis API Routes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

from services.fmv_analysis_engine import FMVAnalysisEngine

logger = logging.getLogger(__name__)
router = APIRouter()


class FMVAnalysisRequest(BaseModel):
    """Request for FMV analysis"""
    budgeted_costs: List[Dict[str, Any]]
    tolerance: Optional[float] = 0.25


class FMVAnalysisResponse(BaseModel):
    """Response from FMV analysis"""
    success: bool
    analysis: Dict[str, Any]
    recommendations: List[str]


@router.post("/fmv/analyze", response_model=FMVAnalysisResponse)
async def analyze_fmv(request: FMVAnalysisRequest):
    """
    Analyze budgeted costs against Fair Market Value benchmarks
    """
    try:
        logger.info(f"🔍 FMV Analysis requested for {len(request.budgeted_costs)} procedures")
        
        # Initialize FMV engine
        fmv_engine = FMVAnalysisEngine()
        
        # Perform analysis
        analysis_results = fmv_engine.analyze_procedure_costs(
            request.budgeted_costs,
            request.tolerance
        )
        
        # Generate recommendations
        recommendations = fmv_engine.get_recommendations(analysis_results)
        
        logger.info("✅ FMV Analysis complete")
        
        return FMVAnalysisResponse(
            success=True,
            analysis=analysis_results,
            recommendations=recommendations
        )
        
    except Exception as e:
        logger.error(f"❌ Error in FMV analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fmv/benchmarks")
async def get_benchmarks():
    """
    Get available FMV benchmarks
    """
    try:
        fmv_engine = FMVAnalysisEngine()
        benchmarks = fmv_engine.benchmarks
        
        # Group by category
        by_category = {}
        for procedure, data in benchmarks.items():
            category = data['category']
            if category not in by_category:
                by_category[category] = []
            by_category[category].append({
                'procedure': procedure,
                'median': data['median'],
                'q1': data['q1'],
                'q3': data['q3']
            })
        
        return {
            'success': True,
            'benchmarks': benchmarks,
            'by_category': by_category,
            'total_benchmarks': len(benchmarks)
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting benchmarks: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

