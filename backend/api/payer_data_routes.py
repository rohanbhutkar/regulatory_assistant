"""
Payer Data API Routes - LLM-accessible endpoints for payer data operations
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from services.payer_data_service import payer_data_service
from utils.optimized_data_loader import OptimizedDataLoader

router = APIRouter(prefix="/payer-data", tags=["Payer Data"])


class DrugCoverageRequest(BaseModel):
    """Request model for drug coverage lookup"""
    drug_name: str
    indication: Optional[str] = None


class ComparatorCoverageRequest(BaseModel):
    """Request model for comparator coverage lookup"""
    comparators: List[Dict[str, Any]]
    indication: Optional[str] = None


class ProductSearchRequest(BaseModel):
    """Request model for product search"""
    query: str
    therapeutic_area: Optional[str] = None
    max_results: int = 50


def get_data_loader() -> OptimizedDataLoader:
    """Dependency to get data loader"""
    loader = OptimizedDataLoader()
    payer_data_service.data_loader = loader
    return loader


@router.post("/coverage")
async def get_drug_coverage(
    request: DrugCoverageRequest,
    loader: OptimizedDataLoader = Depends(get_data_loader)
) -> Dict[str, Any]:
    """
    Get formulary coverage for a drug.
    LLM-accessible endpoint for coverage queries.
    """
    try:
        coverage = payer_data_service.get_formulary_coverage(
            request.drug_name,
            request.indication
        )
        
        if coverage:
            return {
                "success": True,
                "drug_name": request.drug_name,
                "coverage": coverage
            }
        else:
            return {
                "success": False,
                "drug_name": request.drug_name,
                "message": "No coverage information found"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/coverage/batch")
async def get_batch_coverage(
    drug_names: List[str],
    indication: Optional[str] = None,
    loader: OptimizedDataLoader = Depends(get_data_loader)
) -> Dict[str, Any]:
    """
    Get formulary coverage for multiple drugs.
    LLM-accessible batch endpoint.
    """
    try:
        results = payer_data_service.search_formulary_coverage(
            drug_names,
            indication
        )
        
        return {
            "success": True,
            "count": len(results),
            "coverage": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/comparators/coverage")
async def get_comparator_coverage(
    request: ComparatorCoverageRequest,
    loader: OptimizedDataLoader = Depends(get_data_loader)
) -> Dict[str, Any]:
    """
    Get coverage information for a list of comparators.
    Enhances comparator list with coverage data.
    """
    try:
        enhanced = payer_data_service.get_comparator_coverage(
            request.comparators,
            request.indication
        )
        
        return {
            "success": True,
            "comparators": enhanced,
            "count": len(enhanced)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/products/search")
async def search_products(
    request: ProductSearchRequest,
    loader: OptimizedDataLoader = Depends(get_data_loader)
) -> Dict[str, Any]:
    """
    Search for products by name, generic name, or therapeutic area.
    LLM-accessible product search.
    """
    try:
        products = payer_data_service.search_products(
            request.query,
            request.therapeutic_area,
            request.max_results
        )
        
        return {
            "success": True,
            "query": request.query,
            "products": products,
            "count": len(products)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/product/{drug_name}")
async def get_product_info(
    drug_name: str,
    indication: Optional[str] = Query(None),
    loader: OptimizedDataLoader = Depends(get_data_loader)
) -> Dict[str, Any]:
    """
    Get comprehensive product information including coverage, therapeutic area, NDC IDs.
    LLM-accessible comprehensive product lookup.
    """
    try:
        context = payer_data_service.get_llm_context_for_drug(
            drug_name,
            indication
        )
        
        return {
            "success": True,
            "context": context
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gtn-data")
async def get_gtn_data(
    asset_data: Dict[str, Any],
    comparators: Optional[List[Dict[str, Any]]] = None,
    loader: OptimizedDataLoader = Depends(get_data_loader)
) -> Dict[str, Any]:
    """
    Get GTN-related data for an asset.
    Coordinates data retrieval for GTN calculations.
    """
    try:
        gtn_data = payer_data_service.get_gtn_data_for_asset(
            asset_data,
            comparators
        )
        
        return {
            "success": True,
            "gtn_data": gtn_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/matching-strategies")
async def get_matching_strategies() -> Dict[str, Any]:
    """
    Get information about the matching strategy.
    Useful for LLMs to understand how matching works.
    """
    return {
        "strategy": {
            "name": "sourcemedid via NDC Relationship",
            "description": "Match via ProductbrandID -> ProductndcID -> sourcemedid in Formulary",
            "note": "This is the primary strategy since ProductbrandID is -1 in formulary data"
        },
        "fallback": {
            "name": "Default Coverage",
            "description": "Return default 'Not Listed/Unknown' when no matches found"
        },
        "data_flow": {
            "step_1": "Find product in Productbrand_Dim by drug name",
            "step_2": "Get ProductndcID from Productbrand_Productndc_Relationship_Dim using ProductbrandID",
            "step_3": "Match Formulary_Tier_Dim.sourcemedid to ProductndcID",
            "step_4": "If no match, return default 'Not Listed/Unknown' coverage"
        }
    }
