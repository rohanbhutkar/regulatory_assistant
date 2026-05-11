"""
Financial API Routes - Module 6: Financial Impact & Value Modeling
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
from services.financial_modeling_service import financial_modeling_service
from services.us_gtn_service import us_gtn_service
from services.price_potential_engine import price_potential_engine

router = APIRouter()


class PatientFunnelRequest(BaseModel):
    """Request model for patient funnel calculation"""
    asset_id: str
    market: str
    prevalence: Optional[float] = None
    indication: Optional[str] = None
    diagnosis_rate: float = 0.7
    eligibility_rate: float = 0.5
    access_rate: float = 0.8
    uptake_rate: float = 0.6
    market_share: float = 0.1
    subpopulations: Optional[List[Dict[str, Any]]] = None


class RevenueRequest(BaseModel):
    """Request model for revenue calculation"""
    asset_id: str
    market: str
    net_price: float
    units: float
    years: int = 10


class USGTNRequest(BaseModel):
    """Request model for US GTN calculation"""
    asset_id: str
    channel: str
    wac: float
    tier_distribution: Dict[str, float]
    access_scores: Dict[str, float]
    fees: float = 0.0
    chargebacks: float = 0.0


class NPVRequest(BaseModel):
    """Request model for NPV calculation"""
    asset_id: str
    cash_flows: List[Dict[str, Any]]
    discount_rate: float = 0.10
    probability_of_success: Optional[float] = None


class ROIRequest(BaseModel):
    """Request model for ROI calculation"""
    asset_id: str
    total_investment: float
    total_benefits: float
    discount_rate: float = 0.10
    years: int = 10


class ROICurvesRequest(BaseModel):
    """Request model for ROI curves with multiple scenarios"""
    asset_id: str
    base_investment: float
    base_benefits: float
    discount_rate: float = 0.10
    years: int = 10


@router.post("/patient-funnel")
async def calculate_patient_funnel(request: PatientFunnelRequest):
    """Calculate patient funnel from indications using claims data"""
    # Get data loader for claims-based prevalence calculation
    from utils.optimized_data_loader import OptimizedDataLoader
    from main_complete import data_loader
    
    funnel = financial_modeling_service.calculate_patient_funnel(
        asset_id=request.asset_id,
        market=request.market,
        prevalence=request.prevalence,
        indication=request.indication,
        diagnosis_rate=request.diagnosis_rate,
        eligibility_rate=request.eligibility_rate,
        access_rate=request.access_rate,
        uptake_rate=request.uptake_rate,
        market_share=request.market_share,
        subpopulations=request.subpopulations,
        data_loader=data_loader
    )
    return funnel


@router.get("/funnel/{asset_id}")
async def get_patient_funnel(asset_id: str, market: str):
    """Get patient funnel"""
    funnel = financial_modeling_service.get_patient_funnel(asset_id, market)
    if not funnel:
        # Return empty structure instead of 404
        return {
            "asset_id": asset_id,
            "market": market,
            "prevalence": None,
            "diagnosis_rate": None,
            "eligibility_rate": None,
            "access_rate": None,
            "uptake_rate": None,
            "market_share": None,
            "total_addressable_patients": None,
            "treated_patients": None,
            "message": "Patient funnel not calculated yet. Use POST /patient-funnel to calculate."
        }
    return funnel


@router.post("/revenue")
async def calculate_revenue(request: RevenueRequest):
    """Calculate revenue trajectory"""
    revenue = financial_modeling_service.calculate_revenue(
        asset_id=request.asset_id,
        market=request.market,
        net_price=request.net_price,
        units=request.units,
        years=request.years
    )
    return revenue


@router.get("/gtn/{asset_id}/{market}")
async def get_gtn(asset_id: str, market: str):
    """Get GTN calculation"""
    # Get from price potential engine if available
    from services.price_potential_engine import price_potential_engine
    price_prediction = price_potential_engine.get_price_prediction(asset_id, market)
    
    if price_prediction and price_prediction.get("waterfall_components"):
        waterfall = price_prediction["waterfall_components"]
        return {
            "asset_id": asset_id,
            "market": market,
            "list_price": waterfall.get("list_price", 0),
            "net_price": waterfall.get("net_price", 0),
            "gtn_percent": waterfall.get("gtn_percent", 0),
            "waterfall_components": waterfall,
            "calculated_at": price_prediction.get("calculated_at")
        }
    
    # Return empty structure instead of error
    return {
        "asset_id": asset_id,
        "market": market,
        "list_price": 0,
        "net_price": 0,
        "gtn_percent": 0,
        "waterfall_components": {},
        "message": "GTN calculation not found. Calculate pricing first."
    }


@router.post("/us-gtn")
async def calculate_us_gtn(request: USGTNRequest):
    """Calculate US GTN"""
    gtn = us_gtn_service.calculate_channel_net_price(
        asset_id=request.asset_id,
        channel=request.channel,
        wac=request.wac,
        tier_distribution=request.tier_distribution,
        access_scores=request.access_scores,
        fees=request.fees,
        chargebacks=request.chargebacks
    )
    return gtn


@router.get("/us-access/{asset_id}")
async def get_us_access_analysis(asset_id: str):
    """Get US access analysis"""
    # Placeholder
    return {"message": "US access analysis"}


@router.post("/npv")
async def calculate_npv(request: NPVRequest):
    """Calculate NPV/rNPV"""
    result = financial_modeling_service.calculate_npv(
        asset_id=request.asset_id,
        cash_flows=request.cash_flows,
        discount_rate=request.discount_rate,
        probability_of_success=request.probability_of_success
    )
    return result


@router.post("/roi")
async def calculate_roi(request: ROIRequest):
    """Calculate ROI with curve"""
    result = financial_modeling_service.calculate_roi(
        asset_id=request.asset_id,
        total_investment=request.total_investment,
        total_benefits=request.total_benefits,
        discount_rate=request.discount_rate,
        years=request.years
    )
    return result


@router.post("/roi-curves")
async def calculate_roi_curves(request: ROICurvesRequest):
    """Calculate ROI curves for multiple scenarios"""
    result = financial_modeling_service.calculate_roi_curves_multiple_scenarios(
        asset_id=request.asset_id,
        base_investment=request.base_investment,
        base_benefits=request.base_benefits,
        discount_rate=request.discount_rate,
        years=request.years
    )
    return result


@router.get("/value-summary/{asset_id}")
async def get_value_summary(asset_id: str, market: str = "US"):
    """Get value summary (NPV, ROI, peak sales, etc.) - aggregates all financial calculations"""
    # Get patient funnel
    funnel = financial_modeling_service.get_patient_funnel(asset_id, market)
    
    # Get revenue projection
    revenue = financial_modeling_service.get_revenue_projection(asset_id, market)
    
    # Get NPV
    npv_key = f"{asset_id}_npv"
    npv_data = financial_modeling_service._financial_projections.get(npv_key)
    
    # Get ROI
    roi_key = f"{asset_id}_roi"
    roi_data = financial_modeling_service._roi_curves.get(roi_key)
    
    return {
        "asset_id": asset_id,
        "market": market,
        "patient_funnel": funnel,
        "revenue_projection": revenue,
        "npv": npv_data.get("npv", 0) if npv_data else 0,
        "rnpv": npv_data.get("rnpv", 0) if npv_data else 0,
        "roi": roi_data.get("roi", 0) if roi_data else 0,
        "peak_sales": revenue.get("peak_sales", 0) if revenue else 0,
        "time_to_peak": revenue.get("time_to_peak_years", 0) if revenue else 0,
        "treated_patients": funnel.get("treated", 0) if funnel else 0
    }


@router.post("/auto-calculate")
async def auto_calculate_financial_metrics(request: Dict[str, Any]):
    """
    Auto-calculate all financial metrics from asset data
    Integrates pricing, patient funnel, revenue, NPV, and ROI
    """
    try:
        asset_id = request.get("asset_id")
        market = request.get("market", "US")
        list_price = request.get("list_price")
        net_price = request.get("net_price")
        indication = request.get("indication")
        
        if not asset_id:
            raise HTTPException(status_code=400, detail="asset_id required")
        
        results = {}
        
            # 1. Calculate patient funnel from indication
        if indication:
            # Get data loader for claims-based prevalence calculation
            try:
                from utils.optimized_data_loader import OptimizedDataLoader
                # Try to get global data loader, fallback to new instance
                try:
                    from main_complete import data_loader as global_data_loader
                    loader = global_data_loader if global_data_loader else OptimizedDataLoader()
                except (ImportError, AttributeError):
                    loader = OptimizedDataLoader()
            except Exception as e:
                print(f"Warning: Could not initialize data loader: {e}")
                loader = None
            
            # INTEGRATION: Gather data from other tabs for patient funnel
            asset_data = request.get("asset_data", {})
            drug_name = asset_data.get("asset_name") or asset_data.get("drug_name")
            
            # Get coverage data from payer data service
            coverage_data = None
            tier_distribution = None
            if drug_name and loader:
                try:
                    from services.payer_data_service import payer_data_service
                    payer_data_service.data_loader = loader
                    coverage_data = payer_data_service.get_formulary_coverage(drug_name, indication)
                    if coverage_data:
                        tier_distribution = coverage_data.get("coverage_distribution", {})
                except Exception as e:
                    print(f"Warning: Could not get coverage data: {e}")
            
            # Get HTA outcome and access risk
            hta_outcome = request.get("hta_outcome")
            hta_access_risk = None
            time_to_reimbursement_months = None
            if asset_id and market:
                try:
                    from services.hta_intelligence_service import hta_intelligence_service
                    if not hta_outcome:
                        # Get predicted HTA outcome
                        hta_result = hta_intelligence_service.predict_hta_outcome_likelihood(
                            asset_id=asset_id,
                            market=market,
                            evidence_strength=0.7,
                            comparator_clarity=0.6
                        )
                        # Determine most likely outcome
                        outcome_likelihood = hta_result.get("outcome_likelihood", {})
                        if outcome_likelihood:
                            hta_outcome = max(outcome_likelihood.items(), key=lambda x: x[1])[0]
                    
                    # Get access risk
                    hta_access_risk = hta_intelligence_service.calculate_access_risk(
                        asset_id=asset_id,
                        market=market
                    )
                    
                    # Get time to reimbursement
                    reimbursement_data = hta_intelligence_service.predict_time_to_reimbursement(
                        asset_id=asset_id,
                        market=market
                    )
                    time_to_reimbursement_months = reimbursement_data.get("time_to_reimbursement_months")
                except Exception as e:
                    print(f"Warning: Could not get HTA data: {e}")
            
            # Get comparators
            comparators = request.get("comparators", [])
            
            # Get tier distribution from GTN breakdown if available
            if not tier_distribution:
                gtn_breakdown = request.get("gtn_breakdown")
                if gtn_breakdown:
                    tier_distribution = gtn_breakdown.get("tier_distribution") or gtn_breakdown.get("coverage_distribution", {}).get("tier_distribution")
            
            # calculate_patient_funnel is not async
            funnel = financial_modeling_service.calculate_patient_funnel(
                asset_id=asset_id,
                market=market,
                indication=indication,
                data_loader=loader,
                coverage_data=coverage_data,
                hta_outcome=hta_outcome,
                tier_distribution=tier_distribution,
                hta_access_risk=hta_access_risk,
                asset_data=asset_data,
                comparators=comparators
            )
            results["patient_funnel"] = funnel
            
            # 2. Calculate revenue from patient funnel and net price
            if net_price and funnel.get("treated"):
                units = funnel.get("treated", 0)
                # Get launch date from asset data if available
                launch_date = request.get("launch_date") or request.get("expected_launch_dates", {}).get(market)
                key_milestone_dates = request.get("key_milestone_dates", {})
                
                revenue = financial_modeling_service.calculate_revenue(
                    asset_id=asset_id,
                    market=market,
                    net_price=net_price,
                    units=units,
                    years=10,
                    launch_date=launch_date,
                    time_to_reimbursement_months=time_to_reimbursement_months,
                    key_milestone_dates=key_milestone_dates,
                    comparators=comparators,
                    base_market_share=funnel.get("base_market_share")
                )
                results["revenue"] = revenue
                
                # 3. Calculate NPV from revenue
                cash_flows = [
                    {
                        "year": r["year"],
                        "cash_flow": r["revenue"] * 0.3  # Assume 30% margin
                    }
                    for r in revenue.get("revenue_trajectory", [])
                ]
                
                # Use launch year as start year for NPV/ROI calculations
                launch_year = revenue.get("launch_year", datetime.now().year)
                
                npv = financial_modeling_service.calculate_npv(
                    asset_id=asset_id,
                    cash_flows=cash_flows,
                    discount_rate=0.10,
                    probability_of_success=0.6  # Assume 60% PoS
                )
                results["npv"] = npv
                
                # 4. Calculate ROI from investment and benefits
                total_investment = request.get("total_investment", revenue.get("peak_sales", 0) * 0.5)
                total_benefits = sum([cf["cash_flow"] for cf in cash_flows])
                
                roi = financial_modeling_service.calculate_roi(
                    asset_id=asset_id,
                    total_investment=total_investment,
                    total_benefits=total_benefits,
                    discount_rate=0.10,
                    years=10,
                    start_year=launch_year
                )
                results["roi"] = roi
                
                # 5. Calculate ROI curves for multiple scenarios
                roi_curves = financial_modeling_service.calculate_roi_curves_multiple_scenarios(
                    asset_id=asset_id,
                    base_investment=total_investment,
                    base_benefits=total_benefits,
                    discount_rate=0.10,
                    years=10,
                    start_year=launch_year
                )
                results["roi_curves"] = roi_curves
        
        return results
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in auto_calculate_financial_metrics: {e}")
        print(error_details)
        raise HTTPException(status_code=500, detail=f"Failed to calculate financial metrics: {str(e)}")

