"""
Complete FastAPI application with:
1. All existing API routes (persona, assets, trials, commercial, data)
2. Full DynamicReasoningEngine with 16+ agents
3. WebSocket for multi-agent research
4. All original functionality preserved
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.responses import JSONResponse
import uvicorn
from contextlib import asynccontextmanager
import os
import sys
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
# Avoid per-request GET lines from httpx/httpcore (noisy; 403s are often publisher policy).
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Import the DynamicReasoningEngine
from graph.dynamic_reasoning_engine import DynamicReasoningEngine

# Import existing API routes
from api import persona_routes, asset_routes, trial_routes, commercial_routes, data_routes, protocol_routes, analysis_routes, site_map_routes, cpp_routes, fmv_routes, insights_routes
from api import asset_strategy_routes, pricing_routes, hta_routes, financial_routes, scenario_routes, data_catalog_routes, asset_ai_routes, reporting_routes, payer_data_routes, regulatory_routes
from services.regulatory_document_store import regulatory_document_store
from utils.optimized_data_loader import OptimizedDataLoader
from services.asset_management_service import asset_management_service
from services.data_catalog_service import data_catalog_service
from services.scenario_engine import scenario_engine
from utils.websocket_manager import WebSocketManager
from utils.activity_logger import activity_logger
from utils.log_capture import log_capture

# Global instances
data_loader = OptimizedDataLoader()
reasoning_engine = None
websocket_manager = WebSocketManager()

# Initialize data loader for all existing routes
data_routes.set_data_loader(data_loader)
asset_routes.set_data_loader(data_loader)
trial_routes.set_data_loader(data_loader)
analysis_routes.set_data_loader(data_loader)  # Initialize analysis routes with engines
insights_routes.set_data_loader(data_loader)  # Initialize insights routes with data loader
asset_strategy_routes.set_data_loader(data_loader)  # Initialize asset strategy routes with data loader

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global reasoning_engine
    
    # Startup
    logger.info("🚀 Starting Complete Clinical Knowledge Agent Platform...")
    
    # Load essential data for existing routes
    logger.info("📊 Loading essential data...")
    await data_loader.load_essential_data()
    logger.info("✅ Essential data loaded")
    
    # Initialize asset management service with data
    logger.info("💼 Initializing AssetManagementService...")
    count = asset_management_service.initialize_from_trialtrove(data_loader)
    logger.info(f"✅ AssetManagementService initialized with {count} assets")
    
    # Initialize data catalog service with auto-registration
    logger.info("📚 Initializing DataCatalogService...")
    data_catalog_service.initialize_from_data_loader(data_loader)
    logger.info(f"✅ DataCatalogService initialized with {len(data_catalog_service._data_sources)} data sources")
    
    # Initialize scenario engine with data loader
    logger.info("🎲 Initializing ScenarioEngine with data integration...")
    scenario_engine.data_loader = data_loader
    logger.info("✅ ScenarioEngine initialized with data-driven parameter distributions")
    
    # Initialize price potential engine with data loader
    from services.price_potential_engine import price_potential_engine
    price_potential_engine.data_loader = data_loader
    logger.info("✅ PricePotentialEngine initialized with CPP SPU and drug costs data")
    
    # Initialize HTA intelligence service with data loader
    from services.hta_intelligence_service import hta_intelligence_service
    hta_intelligence_service.data_loader = data_loader
    logger.info("✅ HTAIntelligenceService initialized with CPP country specs and indications data")
    
    # Initialize Financial Modeling Service with data loader
    from services.financial_modeling_service import financial_modeling_service
    financial_modeling_service.data_loader = data_loader
    logger.info("✅ FinancialModelingService initialized with claims data for patient funnel calculations")
    
    # Initialize AI Scenario Generator with data loader
    from services.ai_scenario_generator import ai_scenario_generator
    ai_scenario_generator.data_loader = data_loader
    logger.info("✅ AIScenarioGenerator initialized with data integration")
    
    # Initialize Activity Logger with WebSocket manager
    logger.info("📡 Initializing Activity Logger...")
    activity_logger.set_websocket_manager(websocket_manager)
    logger.info("✅ Activity Logger initialized with WebSocket broadcasting")
    
    # Initialize Log Capture with WebSocket manager
    logger.info("📝 Initializing Log Capture...")
    log_capture.set_websocket_manager(websocket_manager)
    log_capture.enable()
    logger.info("✅ Log Capture enabled - backend logs will be sent to frontend")
    
    # Initialize DynamicReasoningEngine
    logger.info("🤖 Initializing DynamicReasoningEngine...")
    reasoning_engine = DynamicReasoningEngine()
    active_agents = [k for k, v in reasoning_engine.available_agents.items() if v is not None]
    logger.info(f"✅ DynamicReasoningEngine initialized with {len(active_agents)} active agents")
    logger.info(f"🎯 Active agents: {', '.join(active_agents[:10])}...")
    
    logger.info("🎉 Complete platform ready with all features!")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down...")

app = FastAPI(
    title="Clinical Knowledge Agent Platform - Complete",
    description="Full-featured clinical research platform with multi-agent capabilities",
    version="2.0.0",
    lifespan=lifespan
)

def _cors_allow_origins() -> list:
    base = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]
    extra = (os.getenv("REGULATORY_CORS_ORIGINS") or "").strip()
    if extra:
        base.extend([x.strip() for x in extra.split(",") if x.strip()])
    return base


@app.middleware("http")
async def regulatory_origin_verify_middleware(request: Request, call_next):
    """Require X-Origin-Verify when set (CloudFront → ALB pattern). Health paths exempt."""
    secret = (os.getenv("REGULATORY_ORIGIN_VERIFY_HEADER_VALUE") or "").strip()
    if not secret:
        return await call_next(request)
    path = request.url.path or ""
    if path in ("/health", "/alb-health"):
        return await call_next(request)
    if request.method == "OPTIONS":
        return await call_next(request)
    header_name = (os.getenv("REGULATORY_ORIGIN_VERIFY_HEADER_NAME") or "X-Origin-Verify").strip()
    if request.headers.get(header_name) != secret:
        return JSONResponse({"detail": "Forbidden"}, status_code=403)
    return await call_next(request)


# CORS - Enhanced to handle all origins and preflight requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Include ALL existing API routes
app.include_router(persona_routes.router, prefix="/api/personas", tags=["personas"])
app.include_router(asset_routes.router, prefix="/api/assets", tags=["assets"])
app.include_router(asset_strategy_routes.router, prefix="/api/asset-strategy", tags=["asset-strategy"])
app.include_router(pricing_routes.router, prefix="/api/asset-strategy/pricing", tags=["pricing"])
app.include_router(hta_routes.router, prefix="/api/asset-strategy/hta", tags=["hta"])
app.include_router(financial_routes.router, prefix="/api/asset-strategy/financial", tags=["financial"])
app.include_router(scenario_routes.router, prefix="/api/asset-strategy/scenarios", tags=["scenarios"])
app.include_router(data_catalog_routes.router, prefix="/api/asset-strategy/data-catalog", tags=["data-catalog"])
app.include_router(asset_ai_routes.router, prefix="/api/asset-strategy/ai", tags=["asset-ai"])
app.include_router(reporting_routes.router, prefix="/api/asset-strategy/reports", tags=["reporting"])
app.include_router(trial_routes.router, prefix="/api/trials", tags=["trials"])
app.include_router(commercial_routes.router, prefix="/api/commercial", tags=["commercial"])
app.include_router(data_routes.router, prefix="/api/data", tags=["data"])
app.include_router(protocol_routes.router, prefix="/api/protocol", tags=["protocol"])
app.include_router(analysis_routes.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(site_map_routes.router, prefix="/api/site-map", tags=["site-map"])
app.include_router(cpp_routes.router, tags=["cpp"])
app.include_router(fmv_routes.router, tags=["fmv"])
app.include_router(insights_routes.router, prefix="/api/insights", tags=["insights"])
app.include_router(payer_data_routes.router, prefix="/api", tags=["Payer Data"])
app.include_router(regulatory_routes.router, prefix="/api/regulatory", tags=["regulatory"])

# Health check with both data loader and agent status
@app.get("/health")
async def health_check():
    """Comprehensive health check"""
    agent_status = {}
    if reasoning_engine:
        agent_status = {k: v is not None for k, v in reasoning_engine.available_agents.items()}
    
    return {
        "status": "healthy",
        # Data loader status
        "essential_data_loaded": data_loader.essential_data_loaded,
        "full_data_loaded": data_loader.loaded,
        "data_counts": {
            "trialtrove": len(data_loader.get_data('trialtrove')),
            "sitetrove": len(data_loader.get_data('sitetrove')),
            "claims": len(data_loader.get_data('claims'))
        },
        # Multi-agent status
        "multi_agent_enabled": reasoning_engine is not None,
        "reasoning_engine_ready": reasoning_engine is not None,
        "total_agents": len(reasoning_engine.available_agents) if reasoning_engine else 0,
        "active_agents": len([v for v in agent_status.values() if v]),
        "agents": agent_status
    }


@app.get("/alb-health")
async def alb_health():
    """Minimal OK for AWS ALB / Kubernetes probes (matches TIME_build-style paths)."""
    return {"status": "ok"}


# Agent capabilities endpoint
@app.get("/api/agents")
async def get_agents():
    """Get all available agents and their capabilities"""
    if not reasoning_engine:
        raise HTTPException(status_code=503, detail="Reasoning engine not initialized")
    
    agent_info = {
        "clinical_trials": "Search ClinicalTrials.gov database (450K+ trials)",
        "trialtrove": "Search TrialTrove database (proprietary trial data, 2021+)",
        "site_trove": "Site selection and performance data",
        "site_map": "Geographic site analysis and mapping",
        "aact": "AACT PostgreSQL database for detailed trial information",
        "pubmed": "Search PubMed literature database",
        "biomcp": "BioOntology medical concept search",
        "openfda": "FDA drug labels and safety data",
        "ema_eu": "EMA / EU medicines: JSON (medicines, EPAR, post-auth, non-EPAR, guidance, DHPC, PSUSA, PIP, orphan, shortages, referrals) + ePI FHIR path probing",
        "fda_labels": "FDA structured product labels",
        "simulation": "Trial startup and enrollment simulation",
        "goodrx": "Drug pricing and market data",
        "google_search": "Web search for pharma news and research",
        "china_regulatory": "CDE / NMPA / zwfw China regulatory web discovery (Google CSE + page text)",
        "llm": "General language model for synthesis and analysis",
        "claims_data": "Healthcare claims data analysis (2.9M+ records)",
        "payer_data": "Payer and formulary data",
        "healthcare_analytics": "Healthcare market analytics",
        "nih_reporter": "NIH RePORTER live API (grants and projects)",
        "npi_registry": "CMS NPI Registry live API (providers and organizations)",
        "openalex": "OpenAlex live bibliographic graph API",
        "crossref": "Crossref REST API (DOI metadata)",
        "ror": "ROR research organization registry API",
        "open_payments": "CMS Open Payments live API (datasets / optional datastore)",
        "eu_ctis": "EU CTIS public trial search API",
        "isrctn": "ISRCTN registry live API",
        "cms_open_data": "CMS data.cms.gov facility datasets (hospital / FQHC enrollments)",
        "fda_datadashboard": "FDA Data Dashboard API (inspections / refusals; credentials required)",
    }
    
    active_agents = {k: v is not None for k, v in reasoning_engine.available_agents.items()}
    
    return {
        "total_agents": len(reasoning_engine.available_agents),
        "active_agents": len([v for v in active_agents.values() if v]),
        "agents": {
            name: {
                "active": active_agents.get(name, False),
                "description": agent_info.get(name, "Agent description not available")
            }
            for name in reasoning_engine.available_agents.keys()
        }
    }

# WebSocket endpoint for multi-agent research (port 8001 style)
@app.websocket("/ws/{client_id}")
async def websocket_multiagent(websocket: WebSocket, client_id: str):
    """WebSocket for real-time multi-agent research queries"""
    await websocket_manager.connect(websocket, client_id)
    logger.info(f"🔌 Multi-Agent WebSocket connected: {client_id}")
    
    try:
        while True:
            data = await websocket.receive_json()
            query_type = data.get("type")
            
            if query_type == "query":
                query = data.get("query", "") or data.get("data", {}).get("query", "")
                conversation_history = data.get("data", {}).get("conversation_history", [])
                study_context = data.get("data", {}).get("study_context", {})
                selected_trials = data.get("data", {}).get("selected_trials", [])
                selected_agents = data.get("data", {}).get("selected_agents") or []
                deep_research = data.get("data", {}).get("deep_research")
                regulatory_document_ids = data.get("data", {}).get("regulatory_document_ids") or []
                regulatory_documents = (
                    regulatory_document_store.get_many(regulatory_document_ids)
                    if regulatory_document_ids
                    else []
                )
                
                logger.info(f"📝 Multi-agent research query from {client_id}: {query}")
                if study_context:
                    logger.info(f"📋 Study context received: {study_context.get('phase')} {study_context.get('indication')} {study_context.get('drugName')}")
                if selected_trials:
                    logger.info(f"🔬 Received {len(selected_trials)} selected trials")
                
                try:
                    # Track if query_started has been sent
                    query_started_sent = False
                    
                    # Progress callback for real-time updates
                    async def progress_callback(progress_data):
                        nonlocal query_started_sent
                        try:
                            # Check if websocket is still connected before sending
                            if websocket.client_state.name == "CONNECTED":
                                # Deep research typed events (envelope: type, run_id, seq, phase, data)
                                dr_types = (
                                    "research_brief_ready",
                                    "research_outline_ready",
                                    "verifier_result",
                                    "replan_started",
                                    "deep_research_phase",
                                    "subruns_merged",
                                )
                                if progress_data.get("type") in dr_types:
                                    await websocket.send_json(progress_data)
                                    return
                                # If this is a graph_plan_ready message, send query_started first
                                if progress_data.get("type") == "graph_plan_ready" and not query_started_sent:
                                    logger.info(f"📋 Sending graph plan to frontend before execution starts")
                                    await websocket.send_json({
                                        "type": "query_started",
                                        "query": query,
                                        "data": {
                                            "graph_plan": progress_data.get("graph_plan")
                                        }
                                    })
                                    query_started_sent = True
                                    return  # Don't send the graph_plan_ready as a node_progress
                                
                                # Send regular progress updates
                                await websocket.send_json({
                                    "type": "node_progress",
                                    "data": progress_data
                                })
                                logger.debug(f"📤 Sent progress update: {progress_data.get('node_id')} - {progress_data.get('status')}")
                        except Exception as e:
                            # Log but don't fail if progress update fails
                            logger.debug(f"⚠️ Progress update failed (client may have disconnected): {str(e)}")
                    
                    # Process query through DynamicReasoningEngine with study context and trials
                    response = await reasoning_engine.process_dynamic_query(
                        query=query,
                        include_graph_plan=True,
                        conversation_history=conversation_history,
                        progress_callback=progress_callback,
                        study_context=study_context,
                        selected_trials=selected_trials,
                        regulatory_documents=regulatory_documents,
                        selected_agents=selected_agents,
                        deep_research=deep_research,
                    )
                    
                    # Send query_started with graph plan if it wasn't sent during execution
                    # (this handles cases where progress_callback wasn't called with graph plan)
                    if websocket.client_state.name == "CONNECTED" and not query_started_sent:
                        logger.warning(f"⚠️ query_started not sent during execution, sending now")
                        graph_plan_dict = None
                        if hasattr(response, 'graph_plan') and response.graph_plan:
                            try:
                                graph_plan_dict = response.graph_plan.dict()
                            except:
                                graph_plan_dict = response.graph_plan if isinstance(response.graph_plan, dict) else None
                        
                        await websocket.send_json({
                            "type": "query_started",
                            "query": query,
                            "data": {
                                "graph_plan": graph_plan_dict
                            }
                        })
                    
                    # Send final response only if still connected
                    if websocket.client_state.name == "CONNECTED":
                        await websocket.send_json({
                            "type": "query_completed",
                            "data": {
                                "synthesis": response.synthesis.dict() if hasattr(response, 'synthesis') else {"answer": str(response)},
                                "graph_plan": response.graph_plan.dict() if hasattr(response, 'graph_plan') and response.graph_plan else None,
                                "metadata": response.metadata.dict() if hasattr(response, 'metadata') else {}
                            }
                        })
                        logger.info(f"✅ Multi-agent query completed for {client_id}")
                    else:
                        logger.warning(f"⚠️ Client {client_id} disconnected before query completion")
                
                except Exception as e:
                    logger.error(f"❌ Error processing multi-agent query: {str(e)}")
                    try:
                        if websocket.client_state.name == "CONNECTED":
                            await websocket.send_json({
                                "type": "error",
                                "error": str(e)
                            })
                    except:
                        logger.debug(f"Could not send error to {client_id} - already disconnected")
            
            elif query_type == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        websocket_manager.disconnect(client_id)
        logger.info(f"🔌 Multi-Agent WebSocket disconnected: {client_id}")
    except Exception as e:
        websocket_manager.disconnect(client_id)
        logger.error(f"❌ Multi-Agent WebSocket error for {client_id}: {str(e)}")

# REST endpoint for multi-agent research queries
@app.post("/api/research/query")
async def research_query(request: dict):
    """REST endpoint for multi-agent research queries"""
    if not reasoning_engine:
        raise HTTPException(status_code=503, detail="Reasoning engine not initialized")
    
    query = request.get("query", "")
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    
    logger.info(f"📝 REST multi-agent research query: {query}")
    
    reg_ids = request.get("regulatory_document_ids") or []
    regulatory_documents = regulatory_document_store.get_many(reg_ids) if reg_ids else []
    selected_agents = request.get("selected_agents") or []
    deep_research = request.get("deep_research")

    try:
        # Process query
        response = await reasoning_engine.process_dynamic_query(
            query=query,
            include_graph_plan=True,
            conversation_history=request.get("conversation_history") or [],
            study_context=request.get("study_context"),
            selected_trials=request.get("selected_trials"),
            regulatory_documents=regulatory_documents,
            selected_agents=selected_agents,
            deep_research=deep_research,
        )
        
        # Return result
        return {
            "success": True,
            "synthesis": response.synthesis.dict() if hasattr(response, 'synthesis') else {"answer": str(response)},
            "graph_plan": response.graph_plan.dict() if hasattr(response, 'graph_plan') and response.graph_plan else None,
            "metadata": response.metadata.dict() if hasattr(response, 'metadata') else {}
        }
    
    except Exception as e:
        logger.error(f"❌ Error processing multi-agent query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Serve static files if available
if os.path.exists("../frontend/public"):
    app.mount("/static", StaticFiles(directory="../frontend/public"), name="static")

if __name__ == "__main__":
    uvicorn.run(
        "main_complete:app", 
        host="127.0.0.1", 
        port=8001, 
        reload=False,
        ws_max_size=10 * 1024 * 1024  # 10MB WebSocket message limit for large responses
    )










































