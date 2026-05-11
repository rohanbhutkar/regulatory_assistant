"""
CPP (Clinical Per-Patient) API Routes
Endpoints for procedure mapping, OPAL calculation, pricing, and CPP calculation
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from decimal import Decimal
import logging

from models.cpp_models import (
    OPALInput,
    CPPResult, CPPBreakdown,
    VisitProcedure,
    StudyType, Phase, RuleApplication,
    to_dict
)
from services.fuzzy_matcher import get_fuzzy_matcher
from services.opal_calculator import get_opal_calculator
from services.spu_pricing_service import get_spu_pricing_service
from services.matrix_calculator import get_matrix_calculator
from services.rules_engine import get_rules_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cpp", tags=["CPP"])


# ===================================================================
# Request/Response Models
# ===================================================================

class ProcedureMatchRequest(BaseModel):
    """Request to match procedure text"""
    text: str
    return_alternatives: bool = True


class ProcedureMatchBatchRequest(BaseModel):
    """Request to match multiple procedure texts"""
    texts: List[str]
    return_alternatives: bool = True


class OPALCalculationRequest(BaseModel):
    """Request to calculate OPAL overhead hours"""
    study_type: str
    phase: str
    num_arms: int
    therapeutic_area: Optional[str] = None
    has_tissue_biopsy: bool = False
    has_pk_draws: bool = False
    has_specialized_procedures: bool = False
    has_complex_assessments: bool = False
    num_special_procedures: int = 0
    num_complex_procedures: int = 0


class PricingRequest(BaseModel):
    """Request to get procedure pricing"""
    procedure_codes: List[str]
    country_code: str = "USA"


class MatrixCalculationRequest(BaseModel):
    """Request to calculate procedure × visit matrix"""
    visit_procedures: List[Dict[str, Any]]
    country_code: str = "USA"
    cycles: Optional[Dict[str, int]] = None
    visit_probabilities: Optional[Dict[str, float]] = None


class CPPCalculationRequest(BaseModel):
    """Request to calculate complete CPP"""
    indication: str
    phase: str
    country_code: str = "USA"
    procedures: List[Dict[str, Any]]
    opal_input: Dict[str, Any]
    study_context: Optional[Dict[str, Any]] = None


# ===================================================================
# Endpoints
# ===================================================================

@router.get("/procedures/all")
async def get_all_procedures():
    """
    Get all available procedure codes for selection
    
    Returns complete list of procedures with codes and descriptions
    """
    try:
        from services.procedure_reference_loader import get_procedure_loader
        loader = get_procedure_loader()
        
        # Return all procedures sorted by code
        procedures_list = [
            {
                "code": proc['code'],
                "name": proc['short_desc'],
                "description": proc['long_desc'],
                "level": proc.get('level', ''),
                "group": proc.get('group', '')
            }
            for proc in sorted(loader.procedures.values(), key=lambda x: x['code'])
        ]
        
        return {
            "success": True,
            "procedures": procedures_list,
            "total": len(procedures_list)
        }
    
    except Exception as e:
        logger.error(f"Error getting procedures: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/map-procedure")
async def map_procedure(request: ProcedureMatchRequest):
    """
    Map procedure text to standardized code using fuzzy matching
    
    Returns best match and alternatives with confidence scores
    """
    try:
        matcher = get_fuzzy_matcher()
        match = matcher.match(request.text, request.return_alternatives)
        
        return {
            "success": True,
            "match": to_dict(match)
        }
    
    except Exception as e:
        logger.error(f"Error mapping procedure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/map-procedures-batch")
async def map_procedures_batch(request: ProcedureMatchBatchRequest):
    """
    Map multiple procedure texts at once
    
    Returns list of matches
    """
    try:
        matcher = get_fuzzy_matcher()
        matches = matcher.match_batch(request.texts)
        
        return {
            "success": True,
            "matches": [to_dict(match) for match in matches],
            "count": len(matches)
        }
    
    except Exception as e:
        logger.error(f"Error mapping procedures batch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate-opal")
async def calculate_opal(request: OPALCalculationRequest):
    """
    Calculate OPAL overhead hours based on study characteristics
    
    Returns raw score, modifiers, adjusted score, and staff distribution
    """
    try:
        # Convert request to OPALInput
        opal_input = OPALInput(
            study_type=StudyType(request.study_type),
            phase=Phase(request.phase),
            num_arms=request.num_arms,
            therapeutic_area=request.therapeutic_area,
            has_tissue_biopsy=request.has_tissue_biopsy,
            has_pk_draws=request.has_pk_draws,
            has_specialized_procedures=request.has_specialized_procedures,
            has_complex_assessments=request.has_complex_assessments,
            num_special_procedures=request.num_special_procedures,
            num_complex_procedures=request.num_complex_procedures
        )
        
        calculator = get_opal_calculator()
        result = calculator.calculate(opal_input)
        
        return {
            "success": True,
            "opal": to_dict(result)
        }
    
    except Exception as e:
        logger.error(f"Error calculating OPAL: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/get-pricing")
async def get_pricing(request: PricingRequest):
    """
    Get Fair Market Value pricing for procedures by country
    
    Returns pricing for each procedure code
    """
    try:
        pricing_service = get_spu_pricing_service()
        prices = pricing_service.get_prices_batch(
            request.procedure_codes,
            request.country_code
        )
        
        # Convert to serializable format
        prices_dict = {}
        for code, price_obj in prices.items():
            if price_obj:
                prices_dict[code] = {
                    "code": code,
                    "price": float(price_obj.local_price),
                    "currency": price_obj.currency,
                    "source": price_obj.source
                }
            else:
                prices_dict[code] = None
        
        return {
            "success": True,
            "country_code": request.country_code,
            "prices": prices_dict,
            "count_found": len([p for p in prices_dict.values() if p is not None]),
            "count_missing": len([p for p in prices_dict.values() if p is None])
        }
    
    except Exception as e:
        logger.error(f"Error getting pricing: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate-matrix")
async def calculate_matrix(request: MatrixCalculationRequest):
    """
    Calculate cost matrix (Procedures × Visits)
    
    Returns detailed matrix with per-visit and per-procedure totals
    """
    try:
        # Convert visit_procedures to VisitProcedure objects
        visit_procedures = []
        for vp_dict in request.visit_procedures:
            vp = VisitProcedure(
                visit_name=vp_dict['visit_name'],
                visit_number=vp_dict.get('visit_number', 0),
                procedure_code=vp_dict['procedure_code'],
                procedure_name=vp_dict.get('procedure_name', ''),
                frequency=vp_dict.get('frequency', 1.0),
                is_optional=vp_dict.get('is_optional', False),
                probability=vp_dict.get('probability', 1.0)
            )
            visit_procedures.append(vp)
        
        matrix_calc = get_matrix_calculator()
        cost_matrix = matrix_calc.calculate_cost_matrix(
            visit_procedures,
            request.country_code,
            request.cycles,
            request.visit_probabilities
        )
        
        return {
            "success": True,
            "matrix": to_dict(cost_matrix),
            "grand_total": float(cost_matrix.grand_total),
            "currency": "USD"
        }
    
    except Exception as e:
        logger.error(f"Error calculating matrix: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/calculate-cpp")
async def calculate_cpp(request: CPPCalculationRequest):
    """
    Calculate complete Clinical Per-Patient (CPP) cost
    
    This is the main endpoint that orchestrates:
    1. OPAL calculation
    2. Procedure pricing
    3. Matrix calculation
    4. Rules application
    
    Returns complete CPP with detailed breakdown
    """
    try:
        logger.info(f"Calculating CPP for {request.indication} in {request.country_code}")
        
        # 1. Calculate OPAL overhead
        opal_input = OPALInput(**request.opal_input)
        opal_calc = get_opal_calculator()
        opal_result = opal_calc.calculate(opal_input)
        
        # 2. Convert procedures to VisitProcedure objects
        visit_procedures = []
        for proc_dict in request.procedures:
            vp = VisitProcedure(
                visit_name=proc_dict.get('visit_name', 'Visit 1'),
                visit_number=proc_dict.get('visit_number', 1),
                procedure_code=proc_dict['procedure_code'],
                procedure_name=proc_dict.get('procedure_name', ''),
                frequency=proc_dict.get('frequency', 1.0),
                is_optional=proc_dict.get('is_optional', False),
                probability=proc_dict.get('probability', 1.0)
            )
            visit_procedures.append(vp)
        
        # 3. Calculate cost matrix
        matrix_calc = get_matrix_calculator()
        cost_matrix = matrix_calc.calculate_cost_matrix(
            visit_procedures,
            request.country_code
        )
        
        direct_procedures = cost_matrix.grand_total
        
        # 4. Calculate staff overhead from OPAL
        # Use average hours across visit types
        avg_hours = opal_result.total_overhead_hours
        # Assume $150/hour blended rate for staff
        staff_overhead = Decimal(str(avg_hours)) * Decimal('150.00')
        
        # 5. Calculate other costs
        administration = direct_procedures * Decimal('0.10')  # 10% admin
        travel_stipend = Decimal('500.00')  # Flat rate
        other_direct_costs = Decimal('0.00')
        
        # 6. Apply rules
        context = {
            "country_code": request.country_code,
            "indication": request.indication,
            "phase": request.phase
        }
        
        rules_engine = get_rules_engine()
        total_before_rules = (
            direct_procedures + 
            staff_overhead + 
            administration + 
            travel_stipend + 
            other_direct_costs
        )
        
        rules_result = rules_engine.apply_rules(total_before_rules, context)
        
        country_adjustments = Decimal(str(rules_result['total_adjustment']))
        
        # 7. Calculate overhead and final total
        total_before_overhead = Decimal(str(rules_result['adjusted_amount']))
        overhead_percentage = 20.0  # 20% overhead
        overhead_amount = total_before_overhead * Decimal('0.20')
        total_cpp = total_before_overhead + overhead_amount
        
        # 8. Build breakdown
        breakdown = CPPBreakdown(
            direct_procedures=direct_procedures,
            staff_overhead=staff_overhead,
            administration=administration,
            travel_stipend=travel_stipend,
            other_direct_costs=other_direct_costs,
            country_adjustments=country_adjustments,
            total_before_overhead=total_before_overhead,
            overhead_percentage=overhead_percentage,
            overhead_amount=overhead_amount,
            total_cpp=total_cpp
        )
        
        # 9. Build procedure costs list
        procedure_costs = []
        for i, code in enumerate(cost_matrix.procedures):
            total_cost = cost_matrix.per_procedure_totals[i]
            if total_cost > 0:
                procedure_costs.append({
                    'code': code,
                    'total_cost': float(total_cost)
                })
        
        # 10. Build result
        cpp_result = CPPResult(
            total_cpp=total_cpp,
            currency="USD",
            country_code=request.country_code,
            breakdown=breakdown,
            opal_result=opal_result,
            procedure_costs=procedure_costs,
            rules_applied=[
                RuleApplication(**app) 
                for app in rules_result['rule_applications']
            ],
            matrix_data=to_dict(cost_matrix),
            calculation_metadata={
                "indication": request.indication,
                "phase": request.phase,
                "num_procedures": len(visit_procedures),
                "num_rules_applied": rules_result['num_rules_applied']
            }
        )
        
        logger.info(f"✅ CPP calculated: ${float(total_cpp):.2f}")
        
        return {
            "success": True,
            "cpp": to_dict(cpp_result)
        }
    
    except Exception as e:
        logger.error(f"Error calculating CPP: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules/preview")
async def preview_rules(
    country_code: Optional[str] = None,
    indication: Optional[str] = None,
    phase: Optional[str] = None
):
    """
    Preview rules that would apply to a given context
    
    Useful for showing users what rules will be applied before calculation
    """
    try:
        context = {}
        if country_code:
            context['country_code'] = country_code
        if indication:
            context['indication'] = indication
        if phase:
            context['phase'] = phase
        
        rules_engine = get_rules_engine()
        rules = rules_engine.get_applicable_rules_preview(context)
        
        return {
            "success": True,
            "rules": rules,
            "count": len(rules)
        }
    
    except Exception as e:
        logger.error(f"Error previewing rules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

