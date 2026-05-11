"""
Scenario API Routes - Module 5: Scenario Planning & Decision Simulation
Enhanced with AI-powered scenario generation
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from services.scenario_engine import scenario_engine
from services.ai_scenario_generator import ai_scenario_generator

router = APIRouter()


class CompareScenariosRequest(BaseModel):
    """Request model for comparing scenarios"""
    base_scenario_id: str
    comparison_scenario_id: str


class SensitivityAnalysisRequest(BaseModel):
    """Request model for sensitivity analysis"""
    asset_id: str
    base_scenario: Dict[str, Any]
    parameters: List[str]
    target_metric: str = "npv"


class MonteCarloRequest(BaseModel):
    """Request model for Monte Carlo simulation"""
    asset_id: str
    base_scenario: Dict[str, Any]
    uncertain_parameters: Optional[Dict[str, Dict[str, Any]]] = None
    iterations: int = 5000
    use_data_driven: bool = True  # Auto-suggest parameters from data if not provided


class RunScenarioRequest(BaseModel):
    """Request model for running a scenario"""
    asset_id: str


@router.get("/")
async def list_scenarios(asset_id: Optional[str] = None):
    """List scenarios"""
    # Filter by asset_id if provided
    all_scenarios = list(scenario_engine._scenarios.values())
    if asset_id:
        scenarios = [s for s in all_scenarios if s.get("asset_id") == asset_id]
    else:
        scenarios = all_scenarios
    
    # Sort by created_at if available, otherwise by name
    scenarios.sort(key=lambda x: (
        x.get("created_at") or x.get("calculated_at") or "",
        x.get("name", "")
    ), reverse=True)
    
    return {"scenarios": scenarios, "total": len(scenarios)}


@router.post("/")
async def create_scenario(scenario: Dict[str, Any]):
    """Create a new scenario"""
    # Ensure asset_id is included
    if "asset_id" not in scenario:
        raise HTTPException(status_code=400, detail="asset_id is required")
    
    scenario_id = scenario_engine.save_scenario(scenario)
    return {"scenario_id": scenario_id, "scenario": scenario}


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: str):
    """Get scenario details"""
    scenario = scenario_engine.get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario


@router.put("/{scenario_id}")
async def update_scenario(scenario_id: str, updates: Dict[str, Any]):
    """Update a scenario"""
    scenario = scenario_engine.get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    scenario.update(updates)
    scenario_engine.save_scenario(scenario)
    return scenario


@router.post("/{scenario_id}/run")
async def run_scenario(scenario_id: str, request: RunScenarioRequest):
    """Run a scenario"""
    scenario = scenario_engine.get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    result = scenario_engine.run_deterministic_scenario(request.asset_id, scenario)
    return result


@router.post("/compare")
async def compare_scenarios(request: CompareScenariosRequest):
    """Compare two scenarios"""
    delta = scenario_engine.calculate_scenario_delta(request.base_scenario_id, request.comparison_scenario_id)
    return delta


@router.post("/sensitivity")
async def run_sensitivity_analysis(request: SensitivityAnalysisRequest):
    """Run sensitivity analysis"""
    result = scenario_engine.run_sensitivity_analysis(
        asset_id=request.asset_id,
        base_scenario=request.base_scenario,
        parameters=request.parameters,
        target_metric=request.target_metric
    )
    return result


@router.post("/monte-carlo")
async def run_monte_carlo(request: MonteCarloRequest):
    """Run Monte Carlo simulation with data-driven parameter distributions"""
    result = scenario_engine.run_monte_carlo(
        asset_id=request.asset_id,
        base_scenario=request.base_scenario,
        uncertain_parameters=request.uncertain_parameters,
        iterations=request.iterations,
        use_data_driven=request.use_data_driven
    )
    return result


@router.get("/suggest-parameters/{asset_id}")
async def suggest_uncertain_parameters(asset_id: str, market: str = "US"):
    """Intelligently suggest uncertain parameters based on asset and historical data"""
    suggested = scenario_engine.suggest_uncertain_parameters(asset_id, market)
    return {
        "asset_id": asset_id,
        "market": market,
        "suggested_parameters": suggested,
        "rationale": "Parameters derived from historical data sources (TrialTrove, Claims, Payer data)"
    }


@router.delete("/{scenario_id}")
async def delete_scenario(scenario_id: str):
    """Delete a scenario"""
    scenario = scenario_engine.get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    
    # Remove from storage
    if scenario_id in scenario_engine._scenarios:
        del scenario_engine._scenarios[scenario_id]
    
    return {"message": "Scenario deleted", "scenario_id": scenario_id}


@router.get("/{scenario_id}/results")
async def get_scenario_results(scenario_id: str):
    """Get scenario results"""
    scenario = scenario_engine.get_scenario(scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario.get("results", {})


class AIScenarioRequest(BaseModel):
    """Request model for AI scenario generation"""
    asset_id: str
    scenario_description: str
    asset_context: Optional[Dict[str, Any]] = None
    market: str = "US"
    auto_run: bool = True  # Automatically run the scenario after generation


@router.post("/ai/generate")
async def generate_ai_scenario(request: AIScenarioRequest):
    """
    Generate a scenario from natural language description using AI
    
    Examples:
    - "6 months faster submission with priority review voucher"
    - "Increase list price by $50K but don't get coverage"
    - "Competitor launches 3 months earlier, reduce market share by 20%"
    - "Use priority review voucher, get restricted coverage, increase price by 25%"
    """
    try:
        # Generate scenario from text
        enhanced_scenario = await ai_scenario_generator.generate_scenario_from_text(
            asset_id=request.asset_id,
            scenario_description=request.scenario_description,
            asset_context=request.asset_context,
            market=request.market
        )
        
        # Convert to scenario parameters
        scenario_params = ai_scenario_generator.convert_to_scenario_params(
            enhanced_scenario,
            base_scenario=request.asset_context or {}
        )
        
        # Save scenario
        scenario_id = scenario_engine.save_scenario({
            **scenario_params,
            "asset_id": request.asset_id,
            "market": request.market,
            "scenario_type": "ai_generated",
            "original_description": request.scenario_description
        })
        
        result = {
            "scenario_id": scenario_id,
            "enhanced_scenario": enhanced_scenario,
            "scenario_params": scenario_params,
            "message": "Scenario generated successfully"
        }
        
        # Auto-run if requested
        if request.auto_run:
            run_result = scenario_engine.run_deterministic_scenario(
                request.asset_id,
                scenario_params
            )
            result["run_result"] = run_result
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating AI scenario: {str(e)}")


@router.post("/ai/generate-and-compare")
async def generate_and_compare_scenarios(
    request: AIScenarioRequest,
    base_scenario_id: Optional[str] = None
):
    """
    Generate an AI scenario and compare it to a base scenario
    
    If base_scenario_id is provided, compares against that.
    Otherwise, uses the current asset state as baseline.
    """
    try:
        if not request:
            raise HTTPException(status_code=400, detail="Request body required")
        
        # Generate new scenario
        enhanced_scenario = await ai_scenario_generator.generate_scenario_from_text(
            asset_id=request.asset_id,
            scenario_description=request.scenario_description,
            asset_context=request.asset_context,
            market=request.market
        )
        
        scenario_params = ai_scenario_generator.convert_to_scenario_params(
            enhanced_scenario,
            base_scenario=request.asset_context or {}
        )
        
        # Run new scenario
        new_result = scenario_engine.run_deterministic_scenario(
            request.asset_id,
            scenario_params
        )
        
        new_scenario_id = scenario_engine.save_scenario(new_result)
        
        # Get base scenario for comparison
        if base_scenario_id:
            base_scenario = scenario_engine.get_scenario(base_scenario_id)
            if not base_scenario:
                raise HTTPException(status_code=404, detail="Base scenario not found")
            base_result = base_scenario.get("results", {})
        else:
            # Use current asset state as baseline
            base_params = request.asset_context or {}
            base_result_obj = scenario_engine.run_deterministic_scenario(
                request.asset_id,
                base_params
            )
            base_result = base_result_obj.get("results", {})
            base_scenario_id = base_result_obj.get("scenario_id")
        
        # Calculate deltas
        deltas = {
            "net_price": new_result["results"].get("net_price", 0) - base_result.get("net_price", 0),
            "npv": new_result["results"].get("npv", 0) - base_result.get("npv", 0),
            "rnpv": new_result["results"].get("rnpv", 0) - base_result.get("rnpv", 0),
            "peak_sales": new_result["results"].get("peak_sales", 0) - base_result.get("peak_sales", 0),
            "list_price": new_result["results"].get("list_price", 0) - base_result.get("list_price", 0)
        }
        
        return {
            "base_scenario_id": base_scenario_id,
            "new_scenario_id": new_scenario_id,
            "enhanced_scenario": enhanced_scenario,
            "base_results": base_result,
            "new_results": new_result["results"],
            "deltas": deltas,
            "summary": {
                "npv_change": deltas["npv"],
                "npv_change_percent": (deltas["npv"] / base_result.get("npv", 1)) * 100 if base_result.get("npv") else 0,
                "net_price_change": deltas["net_price"],
                "peak_sales_change": deltas["peak_sales"]
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating and comparing scenarios: {str(e)}")

