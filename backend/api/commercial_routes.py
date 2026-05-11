from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from api_models import SimulationParameters, RevenueSimulationResponse
import uuid
import random

router = APIRouter()

@router.post("/revenue-simulation", response_model=RevenueSimulationResponse)
async def run_revenue_simulation(simulation_params: SimulationParameters):
    """Run comprehensive revenue simulation with progress tracking"""
    
    # Extract parameters
    tpp = simulation_params.tpp_parameters
    payer_split = simulation_params.payer_split
    coverage = simulation_params.coverage_assumptions
    funnel = simulation_params.patient_funnel
    
    # Calculate quarterly revenue
    quarterly_revenue = []
    total_revenue = 0
    peak_revenue = 0
    time_to_peak = 0
    
    for quarter in range(1, 17):  # 4 years
        # Simulate revenue growth curve
        if quarter <= 4:
            # Launch phase - slow growth
            base_revenue = tpp.get("pricing", 1000) * funnel.get("total_population", 1000) * 0.1 * (quarter / 4)
        elif quarter <= 8:
            # Growth phase
            base_revenue = tpp.get("pricing", 1000) * funnel.get("total_population", 1000) * 0.3 * ((quarter - 4) / 4)
        elif quarter <= 12:
            # Peak phase
            base_revenue = tpp.get("pricing", 1000) * funnel.get("total_population", 1000) * 0.6
        else:
            # Decline phase
            base_revenue = tpp.get("pricing", 1000) * funnel.get("total_population", 1000) * 0.4 * ((16 - quarter) / 4)
        
        # Apply payer split and coverage
        commercial_revenue = base_revenue * payer_split.get("commercial", 0.4) * coverage.get("commercial_coverage", 0.8)
        medicare_revenue = base_revenue * payer_split.get("medicare", 0.35) * coverage.get("medicare_coverage", 0.9)
        medicaid_revenue = base_revenue * payer_split.get("medicaid", 0.25) * coverage.get("medicaid_coverage", 0.7)
        
        quarter_revenue = commercial_revenue + medicare_revenue + medicaid_revenue
        
        quarterly_revenue.append({
            "quarter": quarter,
            "year": (quarter - 1) // 4 + 1,
            "quarter_in_year": ((quarter - 1) % 4) + 1,
            "revenue": quarter_revenue,
            "commercial": commercial_revenue,
            "medicare": medicare_revenue,
            "medicaid": medicaid_revenue
        })
        
        total_revenue += quarter_revenue
        
        if quarter_revenue > peak_revenue:
            peak_revenue = quarter_revenue
            time_to_peak = quarter
    
    # Calculate patient funnel results
    patient_funnel_results = {
        "total_population": funnel.get("total_population", 1000),
        "indication_prevalence": funnel.get("indication_prevalence", 0.05),
        "diagnosis_rate": funnel.get("diagnosis_rate", 0.8),
        "treatment_rate": funnel.get("treatment_rate", 0.6),
        "adherence_rate": funnel.get("adherence_rate", 0.85),
        "final_patient_count": int(funnel.get("total_population", 1000) * 
                                  funnel.get("indication_prevalence", 0.05) * 
                                  funnel.get("diagnosis_rate", 0.8) * 
                                  funnel.get("treatment_rate", 0.6) * 
                                  funnel.get("adherence_rate", 0.85))
    }
    
    # Sensitivity analysis
    sensitivity_analysis = {
        "pricing_sensitivity": {
            "baseline": tpp.get("pricing", 1000),
            "high_scenario": tpp.get("pricing", 1000) * 1.2,
            "low_scenario": tpp.get("pricing", 1000) * 0.8,
            "revenue_impact": "±25%"
        },
        "coverage_sensitivity": {
            "baseline": coverage.get("commercial_coverage", 0.8),
            "high_scenario": min(1.0, coverage.get("commercial_coverage", 0.8) + 0.1),
            "low_scenario": max(0.0, coverage.get("commercial_coverage", 0.8) - 0.1),
            "revenue_impact": "±12%"
        }
    }
    
    return RevenueSimulationResponse(
        simulation_id=str(uuid.uuid4()),
        quarterly_revenue=quarterly_revenue,
        total_revenue=total_revenue,
        peak_revenue=peak_revenue,
        time_to_peak=time_to_peak,
        patient_funnel=patient_funnel_results,
        sensitivity_analysis=sensitivity_analysis,
        assumptions={
            "tpp_parameters": tpp,
            "payer_split": payer_split,
            "coverage_assumptions": coverage,
            "patient_funnel": funnel
        },
        simulation_metadata={
            "created_at": "2024-01-15T12:00:00Z",
            "simulation_type": "revenue_curve",
            "version": "1.0"
        }
    )

@router.post("/scenario-analysis")
async def run_scenario_analysis(
    base_scenario: SimulationParameters,
    scenarios: List[Dict[str, Any]]
):
    """Run scenario analysis comparing multiple simulation parameters"""
    
    # Run base scenario
    base_results = await run_revenue_simulation(base_scenario)
    
    # Run alternative scenarios
    scenario_results = []
    for scenario in scenarios:
        # Merge base scenario with scenario-specific parameters
        scenario_params = SimulationParameters(
            tpp_parameters={**base_scenario.tpp_parameters, **scenario.get("tpp_parameters", {})},
            payer_split={**base_scenario.payer_split, **scenario.get("payer_split", {})},
            coverage_assumptions={**base_scenario.coverage_assumptions, **scenario.get("coverage_assumptions", {})},
            patient_funnel={**base_scenario.patient_funnel, **scenario.get("patient_funnel", {})}
        )
        
        scenario_result = await run_revenue_simulation(scenario_params)
        
        scenario_results.append({
            "scenario": scenario,
            "results": scenario_result,
            "differences": {
                "total_revenue_difference": scenario_result.total_revenue - base_results.total_revenue,
                "peak_revenue_difference": scenario_result.peak_revenue - base_results.peak_revenue,
                "time_to_peak_difference": scenario_result.time_to_peak - base_results.time_to_peak
            }
        })
    
    return {
        "base_scenario": base_results,
        "scenarios": scenario_results
    }

@router.post("/patient-funnel-simulation")
async def simulate_patient_funnel(funnel_params: Dict[str, Any]):
    """Simulate patient funnel with interactive parameters"""
    
    total_population = funnel_params.get("total_population", 1000)
    indication_prevalence = funnel_params.get("indication_prevalence", 0.05)
    diagnosis_rate = funnel_params.get("diagnosis_rate", 0.8)
    treatment_rate = funnel_params.get("treatment_rate", 0.6)
    adherence_rate = funnel_params.get("adherence_rate", 0.85)
    
    # Calculate funnel stages
    funnel_stages = [
        {
            "stage": "Total Population",
            "count": total_population,
            "conversion_rate": 1.0,
            "description": "General population"
        },
        {
            "stage": "Indication Population",
            "count": int(total_population * indication_prevalence),
            "conversion_rate": indication_prevalence,
            "description": "Population with target indication"
        },
        {
            "stage": "Diagnosed Population",
            "count": int(total_population * indication_prevalence * diagnosis_rate),
            "conversion_rate": diagnosis_rate,
            "description": "Population diagnosed with condition"
        },
        {
            "stage": "Treatment Population",
            "count": int(total_population * indication_prevalence * diagnosis_rate * treatment_rate),
            "conversion_rate": treatment_rate,
            "description": "Population receiving treatment"
        },
        {
            "stage": "Adherent Population",
            "count": int(total_population * indication_prevalence * diagnosis_rate * treatment_rate * adherence_rate),
            "conversion_rate": adherence_rate,
            "description": "Population adherent to treatment"
        }
    ]
    
    return {
        "funnel_stages": funnel_stages,
        "final_patient_count": funnel_stages[-1]["count"],
        "conversion_rates": [
            {"stage": stage["stage"], "rate": stage["conversion_rate"]} 
            for stage in funnel_stages
        ],
        "optimization_opportunities": [
            {
                "stage": "Diagnosis",
                "current_rate": diagnosis_rate,
                "improvement_potential": 0.15,
                "impact": "Increase diagnosed population by 15%"
            },
            {
                "stage": "Treatment",
                "current_rate": treatment_rate,
                "improvement_potential": 0.1,
                "impact": "Increase treatment population by 10%"
            }
        ]
    }

@router.post("/sensitivity-analysis")
async def run_sensitivity_analysis(
    base_params: SimulationParameters,
    sensitivity_variables: List[str]
):
    """Run sensitivity analysis on key simulation variables"""
    
    base_results = await run_revenue_simulation(base_params)
    
    sensitivity_results = []
    
    for variable in sensitivity_variables:
        if variable == "pricing":
            # Test pricing sensitivity
            high_params = SimulationParameters(
                tpp_parameters={**base_params.tpp_parameters, "pricing": base_params.tpp_parameters.get("pricing", 1000) * 1.2},
                payer_split=base_params.payer_split,
                coverage_assumptions=base_params.coverage_assumptions,
                patient_funnel=base_params.patient_funnel
            )
            low_params = SimulationParameters(
                tpp_parameters={**base_params.tpp_parameters, "pricing": base_params.tpp_parameters.get("pricing", 1000) * 0.8},
                payer_split=base_params.payer_split,
                coverage_assumptions=base_params.coverage_assumptions,
                patient_funnel=base_params.patient_funnel
            )
            
            high_results = await run_revenue_simulation(high_params)
            low_results = await run_revenue_simulation(low_params)
            
            sensitivity_results.append({
                "variable": variable,
                "range": [base_params.tpp_parameters.get("pricing", 1000) * 0.8, base_params.tpp_parameters.get("pricing", 1000) * 1.2],
                "impact": (high_results.total_revenue - low_results.total_revenue) / base_results.total_revenue,
                "scenarios": [
                    {"name": "Low", "value": base_params.tpp_parameters.get("pricing", 1000) * 0.8, "revenue": low_results.total_revenue},
                    {"name": "Baseline", "value": base_params.tpp_parameters.get("pricing", 1000), "revenue": base_results.total_revenue},
                    {"name": "High", "value": base_params.tpp_parameters.get("pricing", 1000) * 1.2, "revenue": high_results.total_revenue}
                ]
            })
    
    return {
        "base_results": base_results,
        "sensitivity_variables": sensitivity_results
    }

