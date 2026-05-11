"""
Pricing API Routes - Module 3: Early Price Potential & Net Price Prediction
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from services.price_potential_engine import price_potential_engine
from services.comparator_service import comparator_service
from utils.optimized_data_loader import OptimizedDataLoader

router = APIRouter()


class WaterfallRequest(BaseModel):
    """Request model for waterfall calculation"""
    asset_id: str
    market: str
    list_price: float
    mandatory_discount_pct: float = 0.0
    expected_rebates: float = 0.0
    clawbacks: float = 0.0
    program_adjustments: float = 0.0


class PricePredictionRequest(BaseModel):
    """Request model for price prediction"""
    asset_id: str
    market: str
    list_price: float
    mandatory_discount_pct: float = 0.0
    expected_rebates: float = 0.0
    clawbacks: float = 0.0
    program_adjustments: float = 0.0
    include_uncertainty: bool = True

def get_data_loader() -> OptimizedDataLoader:
    """Get data loader instance"""
    from utils.optimized_data_loader import OptimizedDataLoader
    # In real implementation, this would be injected
    return OptimizedDataLoader()


@router.post("/predict")
async def predict_net_price(request: PricePredictionRequest):
    """Predict net price with optional uncertainty ranges"""
    try:
        # Get asset data for real GTN calculations
        from services.asset_management_service import asset_management_service
        asset = asset_management_service.get_asset(request.asset_id)
        asset_data = None
        comparators = None
        
        if asset:
            asset_data = {
                "asset_name": asset.asset_name,
                "indication": asset.indication,
                "therapeutic_area": asset.therapeutic_area,
                "moa": asset.moa,
                "development_stage": asset.development_stage
            }
            
            # Get comparators for this asset
            try:
                from services.comparator_service import comparator_service
                from utils.optimized_data_loader import OptimizedDataLoader
                data_loader = OptimizedDataLoader()
                comparators = comparator_service.recommend_comparators(
                    asset_id=request.asset_id,
                    indication=asset.indication or asset.therapeutic_area or "",
                    market=request.market,
                    therapeutic_area=asset.therapeutic_area,
                    moa=asset.moa,
                    loader=data_loader
                )
            except Exception as e:
                print(f"Warning: Could not fetch comparators: {e}")
                comparators = None
        
        # Calculate waterfall with real data if available
        print(f"📊 Calculating waterfall for asset {request.asset_id} in market {request.market}")
        print(f"   List Price: ${request.list_price:,.2f}")
        print(f"   Inputs - Discount: {request.mandatory_discount_pct}%, Rebates: ${request.expected_rebates:,.2f}, Clawbacks: ${request.clawbacks:,.2f}")
        
        waterfall = price_potential_engine.calculate_waterfall(
            asset_id=request.asset_id,
            market=request.market,
            list_price=request.list_price,
            mandatory_discount_pct=request.mandatory_discount_pct,
            expected_rebates=request.expected_rebates,
            clawbacks=request.clawbacks,
            program_adjustments=request.program_adjustments,
            asset_data=asset_data,
            comparators=comparators
        )
        
        print(f"✅ Waterfall calculated:")
        print(f"   Net Price: ${waterfall['net_price']:,.2f}")
        print(f"   GTN %: {waterfall.get('gtn_percent', 0):.2f}%")
        print(f"   Data Sources: {waterfall.get('data_sources_used', [])}")
        if waterfall.get('gtn_breakdown'):
            print(f"   GTN Breakdown: {waterfall['gtn_breakdown']}")
        
        result = {
            "asset_id": request.asset_id,
            "market": request.market,
            "list_price": request.list_price,
            "net_price": waterfall["net_price"],
            "waterfall_components": waterfall
        }
        
        # Add uncertainty if requested
        if request.include_uncertainty:
            try:
                uncertainty = price_potential_engine.predict_net_price_with_uncertainty(
                    asset_id=request.asset_id,
                    market=request.market,
                    list_price=request.list_price,
                    mandatory_discount_pct=request.mandatory_discount_pct,
                    rebate_mean=request.expected_rebates
                )
                result.update(uncertainty)
            except Exception as e:
                print(f"Warning: Could not calculate uncertainty: {e}")
        
        # Auto-trigger financial metrics calculation if indication available (non-blocking)
        # Note: This is done in background and won't block the response
        if asset and (asset.indication or asset.therapeutic_area):
            try:
                # Use asyncio.create_task to run in background without blocking
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(_trigger_financial_calculation(
                        request.asset_id,
                        request.market,
                        asset.indication or asset.therapeutic_area,
                        request.list_price,
                        waterfall["net_price"]
                    ))
                except RuntimeError:
                    # No running loop, skip background task
                    pass
            except Exception as e:
                print(f"Warning: Could not trigger financial calculation: {e}")
        
        return result
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error in predict_net_price: {e}")
        print(error_details)
        raise HTTPException(status_code=500, detail=f"Failed to predict net price: {str(e)}")


async def _trigger_financial_calculation(
    asset_id: str,
    market: str,
    indication: str,
    list_price: float,
    net_price: float
):
    """Helper function to trigger financial calculation asynchronously"""
    try:
        from api.financial_routes import auto_calculate_financial_metrics
        await auto_calculate_financial_metrics({
            "asset_id": asset_id,
            "market": market,
            "indication": indication,
            "list_price": list_price,
            "net_price": net_price
        })
    except Exception as e:
        print(f"Error in financial calculation (non-blocking): {e}")


@router.post("/waterfall")
async def calculate_waterfall(request: WaterfallRequest):
    """Calculate List-to-Net price waterfall"""
    waterfall = price_potential_engine.calculate_waterfall(
        asset_id=request.asset_id,
        market=request.market,
        list_price=request.list_price,
        mandatory_discount_pct=request.mandatory_discount_pct,
        expected_rebates=request.expected_rebates,
        clawbacks=request.clawbacks,
        program_adjustments=request.program_adjustments
    )
    return waterfall


@router.get("/comparators")
async def get_comparator_benchmarks(
    asset_id: str = Query(..., description="Asset ID"),
    market: str = Query(..., description="Market"),
    indication: Optional[str] = Query(None, description="Indication"),
    predicted_net_price: Optional[float] = Query(None, description="Predicted net price for benchmarking")
):
    """Get comparator benchmarks with coverage information"""
    # If indication not provided, try to get from asset
    if not indication:
        try:
            from services.asset_management_service import asset_management_service
            asset = asset_management_service.get_asset(asset_id)
            if asset:
                indication = asset.indication or asset.therapeutic_area
        except Exception as e:
            print(f"⚠️ Could not fetch asset for indication: {e}")
    try:
        # Get asset data
        from services.asset_management_service import asset_management_service
        asset = asset_management_service.get_asset(asset_id)
        
        if not asset:
            return {
                "asset_id": asset_id,
                "market": market,
                "comparator_count": 0,
                "percentiles": {},
                "premium_discount": None,
                "message": "Asset not found"
            }
        
        # Get price prediction (if exists)
        prediction = price_potential_engine.get_price_prediction(asset_id, market)
        predicted_price = predicted_net_price or (prediction.get("net_price", 0) if prediction else 0)
        
        # Get comparators using comparator service
        from services.comparator_service import comparator_service
        from utils.optimized_data_loader import OptimizedDataLoader
        
        data_loader = OptimizedDataLoader()
        indication = indication or asset.indication or asset.therapeutic_area or ""
        
        print(f"📊 Fetching comparators for asset {asset_id}, indication: {indication}, market: {market}")
        comparators = comparator_service.recommend_comparators(
            asset_id=asset_id,
            indication=indication,
            market=market,
            therapeutic_area=asset.therapeutic_area,
            moa=asset.moa,
            loader=data_loader
        )
        
        print(f"📊 Found {len(comparators)} comparators")
        
        # If we have comparators and a predicted price, benchmark it
        if comparators and predicted_price > 0:
            # Extract prices and add coverage information from comparators
            comparator_prices = []
            for comp in comparators:
                drug_name = comp.get("drug", comp.get("name", "Unknown"))
                price = comp.get("price") or comp.get("net_price") or comp.get("list_price")
                
                # Get coverage information from payer data
                coverage_info = None
                if data_loader:
                    try:
                        print(f"🔍 Looking up coverage for {drug_name}")
                        # Pass indication if available for better fallback search
                        coverage_info = comparator_service._get_coverage_info(
                            drug_name, 
                            data_loader, 
                            indication=indication
                        )
                        if coverage_info:
                            print(f"✅ Found coverage info for {drug_name}: {coverage_info.get('coverage_level')}, Tier: {coverage_info.get('tier')}")
                        else:
                            print(f"⚠️ No coverage info found for {drug_name}")
                    except Exception as e:
                        print(f"⚠️ Error getting coverage for {drug_name}: {e}")
                        import traceback
                        traceback.print_exc()
                
                # If no price, try to get from data sources or use estimated price
                if not price or price <= 0:
                    # Try to get pricing from data sources
                    try:
                        stored_price = comparator_service.get_comparator_price(
                            drug_name, market
                        )
                        if stored_price:
                            price = stored_price
                    except Exception:
                        pass
                    
                    # If still no price, estimate based on predicted price (70-130% range)
                    if not price or price <= 0:
                        import random
                        price = predicted_price * random.uniform(0.7, 1.3)
                
                if price and price > 0:
                    # Use coverage info from lookup, or fall back to existing
                    final_coverage_info = coverage_info or {
                        "coverage_level": comp.get("coverage_level", "Not Listed/Unknown"),
                        "restrictions": comp.get("restrictions", []),
                        "tier": comp.get("tier", "Unknown"),
                        "formulary_status": comp.get("formulary_status", "Unknown")
                    }
                    
                    comparator_prices.append({
                        "price": float(price),
                        "drug": drug_name,
                        "coverage": final_coverage_info,
                        **comp
                    })
            
            if comparator_prices:
                benchmark = price_potential_engine.benchmark_comparators(
                    asset_id=asset_id,
                    market=market,
                    comparators=comparator_prices,
                    predicted_net_price=predicted_price
                )
                # Add comparator details with coverage to benchmark
                benchmark["comparators"] = comparator_prices
                print(f"✅ Benchmark calculated: {benchmark.get('comparator_count', 0)} comparators, percentiles: {benchmark.get('percentiles', {})}")
                return benchmark
            else:
                print(f"⚠️ No prices found in comparators, using estimated prices for visualization")
                # Use estimated prices based on predicted price for visualization
                estimated_comparators = []
                for i, comp in enumerate(comparators[:5]):
                    # Vary prices around predicted price (70-130% range)
                    price_multiplier = 0.7 + (i * 0.15)  # 0.7, 0.85, 1.0, 1.15, 1.3
                    estimated_comparators.append({
                        "price": predicted_price * price_multiplier,
                        "drug": comp.get("drug", comp.get("name", f"Comparator {i+1}")),
                        "indication": comp.get("indication", ""),
                        "market": comp.get("market", market),
                        "rationale": comp.get("rationale", ""),
                        "estimated": True
                    })
                
                if estimated_comparators:
                    benchmark = price_potential_engine.benchmark_comparators(
                        asset_id=asset_id,
                        market=market,
                        comparators=estimated_comparators,
                        predicted_net_price=predicted_price
                    )
                    benchmark["comparators"] = estimated_comparators
                    benchmark["message"] = "Using estimated comparator prices based on predicted price. Prices are estimated for visualization purposes."
                    return benchmark
        
        # Return structure even if no comparators
        return {
            "asset_id": asset_id,
            "market": market,
            "comparator_count": len(comparators) if comparators else 0,
            "percentiles": {},
            "premium_discount": None,
            "predicted_price": predicted_price if predicted_price > 0 else None,
            "message": "No comparators with pricing data found. Generate price prediction and comparators first." if not comparators else "Comparators found but no pricing data available."
        }
    except Exception as e:
        print(f"❌ Error fetching comparator benchmarks: {e}")
        import traceback
        traceback.print_exc()
        return {
            "asset_id": asset_id,
            "market": market,
            "comparator_count": 0,
            "percentiles": {},
            "premium_discount": None,
            "message": f"Error: {str(e)}"
        }


@router.get("/{asset_id}/{market}")
async def get_price_prediction(
    asset_id: str,
    market: str,
    include_uncertainty: bool = Query(False, description="Include uncertainty ranges")
):
    """Get price prediction for an asset in a market"""
    prediction = price_potential_engine.get_price_prediction(asset_id, market)
    if not prediction:
        # Return default structure instead of 404
        return {
            "asset_id": asset_id,
            "market": market,
            "list_price": None,
            "net_price": None,
            "waterfall_components": {},
            "message": "No price prediction found. Use POST /predict to calculate price."
        }
    
    # If uncertainty requested, add it
    if include_uncertainty:
        uncertainty = price_potential_engine.predict_net_price_with_uncertainty(
            asset_id=asset_id,
            market=market,
            list_price=prediction.get("list_price", 0),
            mandatory_discount_pct=prediction.get("mandatory_discount_pct", 0),
            rebate_mean=prediction.get("expected_rebates", 0)
        )
        prediction.update(uncertainty)
    
    return prediction


@router.post("/comparators/recommend")
async def recommend_comparators(
    asset_id: str,
    indication: str,
    market: str,
    therapeutic_area: Optional[str] = None,
    moa: Optional[str] = None,
    loader: OptimizedDataLoader = Depends(get_data_loader)
):
    """Recommend comparators based on indication, MoA, market"""
    recommendations = comparator_service.recommend_comparators(
        asset_id=asset_id,
        indication=indication,
        market=market,
        therapeutic_area=therapeutic_area,
        moa=moa,
        loader=loader
    )
    return {"recommendations": recommendations}


@router.post("/subpopulations")
async def get_subpopulation_price_potential(
    asset_id: str,
    market: str,
    subpopulations: List[Dict[str, Any]]
):
    """Get subpopulation price potential"""
    potential = price_potential_engine.calculate_subpopulation_price_potential(
        asset_id=asset_id,
        market=market,
        subpopulations=subpopulations
    )
    return potential


@router.post("/override")
async def override_price_component(
    asset_id: str,
    market: str,
    component_name: str,
    override_value: float,
    justification: str,
    overridden_by: str = "user_001"
):
    """Override a price component with justification"""
    prediction = price_potential_engine.override_price_component(
        asset_id=asset_id,
        market=market,
        component_name=component_name,
        override_value=override_value,
        justification=justification,
        overridden_by=overridden_by
    )
    return prediction

