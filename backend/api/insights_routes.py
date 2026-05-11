"""
API routes for AI-driven insights generation
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from agents.insights_agent import get_insights_agent
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Global reference to data loader (set by main_complete.py)
data_loader = None

def set_data_loader(loader):
    """Set data loader for insights agent"""
    global data_loader
    data_loader = loader
    logger.info("✅ Insights routes initialized with data loader")

class InsightsRequest(BaseModel):
    tab: str
    study_context: Dict[str, Any]
    selected_trials: Optional[List[Dict[str, Any]]] = None
    selected_sites: Optional[List[Dict[str, Any]]] = None

class InsightsResponse(BaseModel):
    success: bool
    insights: List[Dict[str, Any]]
    tab: str
    count: int

@router.post("/generate", response_model=InsightsResponse)
async def generate_insights(request: InsightsRequest):
    """
    Generate AI-driven insights for a specific tab
    
    Returns analytical insights, benchmarking, warnings, and optimization opportunities
    """
    try:
        logger.info(f"🔮 Generating insights for tab: {request.tab}")
        logger.info(f"   Study context keys: {list(request.study_context.keys())}")
        logger.info(f"   Selected trials: {len(request.selected_trials or [])}")
        logger.info(f"   Selected sites: {len(request.selected_sites or [])}")
        
        if data_loader is None:
            raise HTTPException(status_code=500, detail="Data loader not initialized")
        
        agent = get_insights_agent(data_loader)
        
        insights = await agent.generate_insights(
            tab=request.tab,
            study_context=request.study_context,
            selected_trials=request.selected_trials,
            selected_sites=request.selected_sites
        )
        
        logger.info(f"✅ Generated {len(insights)} insights for {request.tab}")
        
        return InsightsResponse(
            success=True,
            insights=insights,
            tab=request.tab,
            count=len(insights)
        )
        
    except Exception as e:
        logger.error(f"❌ Error generating insights: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def insights_health():
    """Health check for insights service"""
    return {
        "status": "healthy",
        "service": "insights",
        "data_loader_initialized": data_loader is not None
    }

