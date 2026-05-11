from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from api_models import Persona, PersonaDashboard, PersonaPermissions

router = APIRouter()

# Persona definitions
PERSONAS = [
    Persona(
        id="asset_management",
        name="Portfolio Management",
        description="Portfolio oversight and investment tracking",
        icon="TrendingUp",
        permissions=["portfolio_view", "cost_analysis", "revenue_projection"],
        dashboard_route="/asset-management",
        features=["portfolio_overview", "cost_analysis", "revenue_modeling", "risk_assessment"]
    ),
    Persona(
        id="study_designer",
        name="Study Designer",
        description="Protocol design and trial planning",
        icon="FileText",
        permissions=["protocol_authoring", "trial_design", "site_selection"],
        dashboard_route="/study-designer",
        features=["trial_design", "protocol_authoring", "site_selection", "ie_optimization", "simulation"]
    ),
    Persona(
        id="commercial",
        name="Commercial",
        description="Market analysis and revenue modeling",
        icon="BarChart3",
        permissions=["market_analysis", "revenue_modeling", "payer_data"],
        dashboard_route="/commercial",
        features=["revenue_modeling", "market_analysis", "payer_analysis", "scenario_planning"]
    ),
    Persona(
        id="regulatory_intelligence",
        name="Regulatory Intelligence",
        description="Document-grounded regulatory assessment and requirement mining",
        icon="Scale",
        permissions=["regulatory_upload", "document_assessment", "requirement_mining"],
        dashboard_route="/regulatory-intelligence",
        features=["document_upload", "requirement_mining", "gap_analysis", "regulatory_chat"]
    )
]

@router.get("/", response_model=List[Persona])
async def get_available_personas():
    """Get all available personas"""
    return PERSONAS

@router.get("/{persona_id}/dashboard", response_model=PersonaDashboard)
async def get_persona_dashboard(persona_id: str):
    """Get persona-specific dashboard data"""
    persona = next((p for p in PERSONAS if p.id == persona_id), None)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    
    # Generate dashboard data based on persona
    if persona_id == "asset_management":
        return PersonaDashboard(
            persona_id=persona_id,
            summary_stats={
                "total_assets": 12,
                "active_trials": 8,
                "total_investment": 150000000,
                "projected_revenue": 450000000
            },
            recent_activity=[
                {"action": "Asset updated", "timestamp": "2024-01-15T10:30:00Z"},
                {"action": "Cost analysis completed", "timestamp": "2024-01-15T09:15:00Z"}
            ],
            quick_actions=["view_portfolio", "run_cost_analysis", "generate_revenue_projection"],
            notifications=[]
        )
    elif persona_id == "study_designer":
        return PersonaDashboard(
            persona_id=persona_id,
            summary_stats={
                "active_trials": 5,
                "protocols_in_design": 3,
                "sites_selected": 45,
                "enrollment_target": 1200
            },
            recent_activity=[
                {"action": "Protocol section updated", "timestamp": "2024-01-15T11:00:00Z"},
                {"action": "Site selection completed", "timestamp": "2024-01-15T08:45:00Z"}
            ],
            quick_actions=["create_trial", "select_sites", "optimize_criteria", "run_simulation"],
            notifications=[]
        )
    elif persona_id == "commercial":
        return PersonaDashboard(
            persona_id=persona_id,
            summary_stats={
                "market_size": 2500000000,
                "revenue_projection": 180000000,
                "payer_coverage": 0.85,
                "market_penetration": 0.12
            },
            recent_activity=[
                {"action": "Revenue simulation completed", "timestamp": "2024-01-15T12:30:00Z"},
                {"action": "Market analysis updated", "timestamp": "2024-01-15T10:00:00Z"}
            ],
            quick_actions=["run_revenue_simulation", "analyze_market", "model_scenarios"],
            notifications=[]
        )
    
    raise HTTPException(status_code=404, detail="Persona not found")

@router.get("/{persona_id}/permissions", response_model=PersonaPermissions)
async def get_persona_permissions(persona_id: str):
    """Get permissions for specific persona"""
    persona = next((p for p in PERSONAS if p.id == persona_id), None)
    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")
    
    return PersonaPermissions(
        persona_id=persona_id,
        permissions=persona.permissions,
        features=persona.features
    )

