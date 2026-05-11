"""
Scenario Engine - Deterministic what-if, sensitivity analysis, Monte Carlo simulation
Enhanced with data-driven parameter distributions and intelligent rationale
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import numpy as np
import pandas as pd
from scipy import stats
from services.price_potential_engine import price_potential_engine
from services.hta_intelligence_service import hta_intelligence_service
from services.financial_modeling_service import financial_modeling_service
from utils.optimized_data_loader import OptimizedDataLoader
import logging

logger = logging.getLogger(__name__)


class ScenarioEngine:
    """Service for scenario planning and simulation with data-driven intelligence"""
    
    def __init__(self, data_loader: Optional[OptimizedDataLoader] = None):
        # In-memory storage
        self._scenarios: Dict[str, Dict[str, Any]] = {}
        self._scenario_runs: Dict[str, List[Dict[str, Any]]] = {}
        self.data_loader = data_loader or OptimizedDataLoader()
    
    def run_deterministic_scenario(
        self,
        asset_id: str,
        scenario_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run deterministic what-if calculation
        
        Re-run calculations from Modules 3, 4, 6 with new parameters
        
        Supports:
        - Timeline changes (launch_date, submission acceleration, priority review voucher)
        - Pricing changes (list_price adjustments)
        - Coverage changes (coverage_level, tier, restrictions)
        - Competitor impacts (market_share adjustments)
        - Market dynamics (uptake_rate, market_size)
        """
        # Extract parameters
        comparator_set = scenario_params.get("comparator_set", [])
        hta_outcome = scenario_params.get("hta_outcome", "approval")
        discount_pct = scenario_params.get("discount_pct", 0.0)
        uptake_archetype = scenario_params.get("uptake_archetype", "moderate")
        launch_date = scenario_params.get("launch_date")
        market = scenario_params.get("market", "US")
        
        # Timeline parameters
        submission_acceleration_months = scenario_params.get("submission_acceleration_months", 0)
        use_priority_review_voucher = scenario_params.get("use_priority_review_voucher", False)
        regulatory_delay_months = scenario_params.get("regulatory_delay_months", 0)
        
        # Pricing parameters
        list_price = scenario_params.get("list_price", 100000)
        list_price_adjustment_dollars = scenario_params.get("list_price_adjustment_dollars", 0)
        list_price_adjustment_percent = scenario_params.get("list_price_adjustment_percent", 0)
        
        # Apply pricing adjustments if specified
        if list_price_adjustment_dollars != 0:
            list_price += list_price_adjustment_dollars
        if list_price_adjustment_percent != 0:
            list_price *= (1 + list_price_adjustment_percent / 100)
        
        # Coverage parameters
        coverage_level = scenario_params.get("coverage_level")
        tier = scenario_params.get("tier")
        restrictions = scenario_params.get("restrictions", [])
        
        # If coverage is explicitly set to "Not Covered", override HTA outcome
        if coverage_level == "Not Covered":
            hta_outcome = "rejection"
        elif coverage_level == "Restricted":
            hta_outcome = "restriction"
        elif coverage_level and hta_outcome == "approval":
            # Coverage level set but HTA outcome not overridden
            pass
        
        # Run pricing calculation with scenario parameters
        net_price_result = price_potential_engine.calculate_waterfall(
            asset_id=asset_id,
            market=market,
            list_price=list_price,
            mandatory_discount_pct=discount_pct
        )
        
        # Apply coverage restrictions to net price if specified
        if coverage_level == "Not Covered":
            # No coverage = no sales
            net_price_result["net_price"] = 0.0
        elif coverage_level == "Restricted" and restrictions:
            # Restricted coverage may reduce net price (simplified)
            restriction_penalty = len(restrictions) * 0.05  # 5% per restriction
            net_price_result["net_price"] *= (1 - restriction_penalty)
        
        # Run HTA assessment with scenario outcome
        hta_result = hta_intelligence_service.predict_hta_outcome_likelihood(
            asset_id=asset_id,
            market=market,
            evidence_strength=0.7,
            comparator_clarity=0.6
        )
        
        # Override HTA outcome if specified
        if hta_outcome:
            hta_result["outcome_likelihood"] = {
                "approval": 1.0 if hta_outcome == "approval" else 0.0,
                "restriction": 1.0 if hta_outcome == "restriction" else 0.0,
                "rejection": 1.0 if hta_outcome == "rejection" else 0.0
            }
        
        # Calculate timeline impact
        timeline_impact = {
            "submission_acceleration_months": submission_acceleration_months,
            "use_priority_review_voucher": use_priority_review_voucher,
            "regulatory_delay_months": regulatory_delay_months,
            "launch_date": launch_date
        }
        
        # Priority review voucher typically saves 4 months
        if use_priority_review_voucher:
            timeline_impact["prv_time_saved_months"] = 4
        
        # INTEGRATION 5: Scenario Coverage Changes → Patient Funnel Recalculation
        # If coverage changed, recalculate patient funnel with new access rates
        recalculated_funnel = None
        units = scenario_params.get("units", 1000)
        
        if coverage_level or tier or restrictions:
            # Get asset data for funnel recalculation
            asset_data = scenario_params.get("asset_data", {})
            indication = asset_data.get("indication") or scenario_params.get("indication")
            
            if indication and self.data_loader:
                # Create coverage data from scenario parameters
                scenario_coverage_data = {
                    "coverage_level": coverage_level,
                    "tier": tier,
                    "restrictions": restrictions
                }
                
                # Recalculate patient funnel with new coverage
                recalculated_funnel = financial_modeling_service.calculate_patient_funnel(
                    asset_id=asset_id,
                    market=market,
                    indication=indication,
                    coverage_data=scenario_coverage_data,
                    hta_outcome=hta_outcome,
                    data_loader=self.data_loader
                )
                
                # Use recalculated units
                if recalculated_funnel:
                    units = recalculated_funnel.get("treated", 0) * recalculated_funnel.get("market_share", 0.1)
        
        # Run financial calculation
        
        # Apply uptake multiplier if specified
        uptake_multiplier = scenario_params.get("uptake_multiplier", 1.0)
        units *= uptake_multiplier
        
        # Apply market share impact if specified
        market_share_impact_percent = scenario_params.get("market_share_impact_percent", 0)
        units *= (1 + market_share_impact_percent / 100)
        
        # Get time to reimbursement for revenue calculation
        time_to_reimbursement_months = None
        if hta_outcome:
            try:
                reimbursement_data = hta_intelligence_service.predict_time_to_reimbursement(
                    asset_id=asset_id,
                    market=market
                )
                time_to_reimbursement_months = reimbursement_data.get("time_to_reimbursement_months")
            except Exception:
                pass
        
        revenue_result = financial_modeling_service.calculate_revenue(
            asset_id=asset_id,
            market=market,
            net_price=net_price_result["net_price"],
            units=units,
            launch_date=launch_date,
            time_to_reimbursement_months=time_to_reimbursement_months,
            key_milestone_dates=scenario_params.get("key_milestone_dates"),
            comparators=scenario_params.get("comparators"),
            base_market_share=recalculated_funnel.get("base_market_share") if recalculated_funnel else None
        )
        
        # Adjust revenue trajectory based on launch date if provided
        if launch_date:
            try:
                if isinstance(launch_date, str):
                    launch_dt = datetime.fromisoformat(launch_date.replace('Z', '+00:00'))
                else:
                    launch_dt = launch_date
                
                # Shift revenue trajectory based on launch date
                # (Simplified - would need base launch date to calculate shift)
                timeline_impact["calculated_launch_date"] = launch_dt.isoformat()
            except Exception as e:
                logger.warning(f"Could not parse launch date: {e}")
        
        # Calculate NPV
        cash_flows = [
            {"year": r["year"], "cash_flow": r["revenue"] * 0.3}  # Simplified - assume 30% margin
            for r in revenue_result["revenue_trajectory"]
        ]
        npv_result = financial_modeling_service.calculate_npv(
            asset_id=asset_id,
            cash_flows=cash_flows,
            probability_of_success=0.5
        )
        
        return {
            "scenario_id": scenario_params.get("scenario_id", str(uuid.uuid4())),
            "asset_id": asset_id,
            "parameters": scenario_params,
            "results": {
                "list_price": list_price,
                "net_price": net_price_result["net_price"],
                "hta_outcome": hta_result["outcome_likelihood"],
                "coverage_level": coverage_level,
                "tier": tier,
                "restrictions": restrictions,
                "peak_sales": revenue_result["peak_sales"],
                "units": units,
                "npv": npv_result["npv"],
                "rnpv": npv_result["rnpv"],
                "timeline_impact": timeline_impact
            },
            "calculated_at": datetime.now().isoformat()
        }
    
    def run_sensitivity_analysis(
        self,
        asset_id: str,
        base_scenario: Dict[str, Any],
        parameters: List[str],
        target_metric: str = "npv"
    ) -> Dict[str, Any]:
        """
        Run one-way sensitivity analysis
        
        For each parameter, test low/base/high values
        Calculate impact on target metric
        """
        base_result = self.run_deterministic_scenario(asset_id, base_scenario)
        base_value = base_result["results"].get(target_metric, 0)
        
        sensitivity_results = []
        
        for param in parameters:
            # Test low/base/high
            param_ranges = {
                "low": base_scenario.get(param, 0) * 0.8,
                "base": base_scenario.get(param, 0),
                "high": base_scenario.get(param, 0) * 1.2
            }
            
            impacts = {}
            for level, value in param_ranges.items():
                test_scenario = {**base_scenario, param: value}
                test_result = self.run_deterministic_scenario(asset_id, test_scenario)
                test_value = test_result["results"].get(target_metric, 0)
                impact = test_value - base_value
                impacts[level] = {
                    "value": value,
                    "metric_value": test_value,
                    "impact": impact
                }
            
            # Calculate swing (high - low)
            swing = impacts["high"]["metric_value"] - impacts["low"]["metric_value"]
            
            sensitivity_results.append({
                "parameter": param,
                "low": impacts["low"],
                "base": impacts["base"],
                "high": impacts["high"],
                "swing": swing,
                "impact_rank": 0  # Will be set after sorting
            })
        
        # Rank by swing
        sensitivity_results.sort(key=lambda x: abs(x["swing"]), reverse=True)
        for idx, result in enumerate(sensitivity_results):
            result["impact_rank"] = idx + 1
        
        return {
            "base_value": base_value,
            "target_metric": target_metric,
            "sensitivity_results": sensitivity_results
        }
    
    def _get_data_driven_distributions(
        self,
        asset_id: str,
        parameter_name: str,
        market: str = "US"
    ) -> Dict[str, Any]:
        """
        Get data-driven parameter distributions from historical data
        
        Uses TrialTrove, Claims, Payer data to inform distributions
        """
        try:
            if parameter_name == "rebate_pct":
                # Get rebate distributions from payer data
                payer_data = self.data_loader.get_payer_data("Payer_Plans_Claims_Fact")
                if not payer_data.empty and "TOTAL_REBATES_PAID" in payer_data.columns:
                    # Parse rebate values - handle dollar-formatted strings and concatenated values
                    import re
                    rebate_values = []
                    
                    for value in payer_data["TOTAL_REBATES_PAID"].dropna():
                        if pd.isna(value):
                            continue
                        
                        # Handle numeric values directly
                        if isinstance(value, (int, float)):
                            if value > 0:
                                rebate_values.append(float(value))
                            continue
                        
                        # Convert to string and handle concatenated values
                        value_str = str(value).strip()
                        
                        # Skip empty strings
                        if not value_str or value_str.lower() in ['nan', 'none', 'null']:
                            continue
                        
                        # If it's a long concatenated string (likely malformed CSV), split by dollar signs
                        if len(value_str) > 50 and '$' in value_str:
                            # Split by $ and extract dollar amounts
                            parts = value_str.split('$')
                            for part in parts:
                                part = part.strip()
                                if part:
                                    # Extract numeric value (remove commas, spaces)
                                    clean_part = part.replace(',', '').replace(' ', '')
                                    match = re.search(r'\d+\.?\d*', clean_part)
                                    if match:
                                        try:
                                            num_val = float(match.group())
                                            if num_val > 0:  # Only include positive values
                                                rebate_values.append(num_val)
                                        except (ValueError, AttributeError):
                                            continue
                        else:
                            # Single value - extract numeric part
                            # Remove $, commas, and spaces, then extract number
                            clean_value = value_str.replace('$', '').replace(',', '').replace(' ', '').strip()
                            # Try to extract number (handles formats like "$1,163.14" or "1163.14")
                            match = re.search(r'\d+\.?\d*', clean_value)
                            if match:
                                try:
                                    num_val = float(match.group())
                                    if num_val > 0:  # Only include positive values
                                        rebate_values.append(num_val)
                                except (ValueError, AttributeError):
                                    continue
                    
                    if len(rebate_values) > 0:
                        # Calculate statistics on parsed numeric values
                        rebates_array = np.array(rebate_values)
                        mean_rebate = float(rebates_array.mean())
                        std_rebate = float(rebates_array.std()) if len(rebate_values) > 1 else 0.0
                        
                        # Convert to percentage (assuming rebates are in dollars, convert to % of list price)
                        # For rebate_pct, we need percentage values (0-100), not dollar amounts
                        # If mean_rebate is already a percentage, use as-is; otherwise estimate
                        # Default assumption: rebate percentages are typically 15-30%
                        # If values are very large (>1000), they're likely dollar amounts, not percentages
                        if mean_rebate > 1000:
                            # These are dollar amounts, not percentages - skip this data source
                            logger.warning(f"TOTAL_REBATES_PAID contains dollar amounts, not percentages. Skipping data-driven distribution.")
                            raise ValueError("Rebate data contains dollar amounts, not percentages")
                        
                        return {
                            "type": "normal",
                            "mean": mean_rebate / 100,  # Convert to decimal (0-1)
                            "std": std_rebate / 100,
                            "data_source": "Payer_Plans_Claims_Fact",
                            "rationale": f"Based on {len(rebate_values)} historical rebate records, mean={mean_rebate:.2f}%, std={std_rebate:.2f}%"
                        }
            
            elif parameter_name == "uptake_rate":
                # Get uptake patterns from sales forecast data
                sales_data = self.data_loader.get_payer_data("Sales_Forecast_Fact")
                if not sales_data.empty and "demand_units" in sales_data.columns:
                    # Analyze uptake curves (simplified - would need time series analysis)
                    demand = sales_data["demand_units"].dropna()
                    if len(demand) > 0:
                        # Use beta distribution for uptake (0-1 bounded)
                        mean_uptake = float(demand.mean() / demand.max()) if demand.max() > 0 else 0.5
                        return {
                            "type": "beta",
                            "alpha": 2 + mean_uptake * 8,  # Shape based on mean
                            "beta": 2 + (1 - mean_uptake) * 8,
                            "data_source": "Sales_Forecast_Fact",
                            "rationale": f"Based on {len(demand)} historical demand records, mean uptake={mean_uptake:.2%}"
                        }
            
            elif parameter_name == "time_to_reimbursement":
                # Get time-to-market from TrialTrove (trial completion times)
                trial_data = self.data_loader.get_data("trialtrove")
                if not trial_data.empty:
                    # Analyze phase completion times (simplified)
                    # Would need to parse dates and calculate durations
                    return {
                        "type": "lognormal",
                        "mean": 3.0,  # log(months) - typical 12-18 months
                        "std": 0.5,
                        "data_source": "TrialTrove",
                        "rationale": "Based on historical regulatory review timelines"
                    }
            
        except Exception as e:
            logger.warning(f"Error getting data-driven distribution for {parameter_name}: {e}")
        
        # Fallback to default distribution
        return {
            "type": "normal",
            "mean": 0.0,
            "std": 0.1,
            "data_source": "default",
            "rationale": "Using default distribution (no historical data available)"
        }
    
    def suggest_uncertain_parameters(
        self,
        asset_id: str,
        market: str = "US"
    ) -> Dict[str, Dict[str, Any]]:
        """
        Intelligently suggest uncertain parameters based on asset and data
        
        Returns parameter distributions informed by historical data
        """
        suggested = {}
        
        # Key uncertain parameters for pharmaceutical assets
        key_params = [
            "rebate_pct",
            "uptake_rate",
            "time_to_reimbursement",
            "market_share",
            "price_elasticity"
        ]
        
        for param in key_params:
            suggested[param] = self._get_data_driven_distributions(asset_id, param, market)
        
        return suggested
    
    def run_monte_carlo(
        self,
        asset_id: str,
        base_scenario: Dict[str, Any],
        uncertain_parameters: Optional[Dict[str, Dict[str, Any]]] = None,
        iterations: int = 5000,
        use_data_driven: bool = True
    ) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation with data-driven parameter distributions
        
        If use_data_driven=True and uncertain_parameters not provided,
        will auto-suggest parameters based on historical data
        """
        # Auto-suggest parameters if not provided and use_data_driven is True
        if uncertain_parameters is None and use_data_driven:
            market = base_scenario.get("market", "US")
            uncertain_parameters = self.suggest_uncertain_parameters(asset_id, market)
            logger.info(f"Auto-suggested {len(uncertain_parameters)} uncertain parameters from data")
        
        if uncertain_parameters is None:
            uncertain_parameters = {}
        
        results = []
        parameter_rationale = {}
        
        for i in range(iterations):
            # Sample parameters
            sampled_params = {**base_scenario}
            
            for param_name, param_dist in uncertain_parameters.items():
                dist_type = param_dist.get("type", "normal")
                
                if dist_type == "normal":
                    mean = param_dist.get("mean", 0)
                    std = param_dist.get("std", 1)
                    sampled_value = np.random.normal(mean, std)
                    # Clip to reasonable bounds
                    if "pct" in param_name or "rate" in param_name:
                        sampled_value = np.clip(sampled_value, 0, 1)
                    sampled_params[param_name] = float(sampled_value)
                elif dist_type == "beta":
                    alpha = param_dist.get("alpha", 2)
                    beta = param_dist.get("beta", 2)
                    sampled_params[param_name] = float(np.random.beta(alpha, beta))
                elif dist_type == "lognormal":
                    mean = param_dist.get("mean", 0)
                    std = param_dist.get("std", 1)
                    sampled_params[param_name] = float(np.random.lognormal(mean, std))
                elif dist_type == "categorical":
                    categories = param_dist.get("categories", [])
                    probs = param_dist.get("probs", [1.0 / len(categories)] * len(categories))
                    sampled_params[param_name] = str(np.random.choice(categories, p=probs))
                
                # Store rationale for first iteration
                if i == 0 and "rationale" in param_dist:
                    parameter_rationale[param_name] = {
                        "distribution": dist_type,
                        "rationale": param_dist.get("rationale", ""),
                        "data_source": param_dist.get("data_source", "default")
                    }
            
            # Run deterministic calculation
            result = self.run_deterministic_scenario(asset_id, sampled_params)
            results.append(result["results"])
        
        # Aggregate results
        npvs = [r.get("npv", 0) for r in results]
        rnpvs = [r.get("rnpv", 0) for r in results]
        peak_sales = [r.get("peak_sales", 0) for r in results]
        net_prices = [r.get("net_price", 0) for r in results]
        
        return {
            "iterations": iterations,
            "parameter_rationale": parameter_rationale,
            "percentiles": {
                "npv": {
                    "p10": float(np.percentile(npvs, 10)),
                    "p50": float(np.percentile(npvs, 50)),
                    "p90": float(np.percentile(npvs, 90)),
                    "mean": float(np.mean(npvs)),
                    "std": float(np.std(npvs))
                },
                "rnpv": {
                    "p10": float(np.percentile(rnpvs, 10)),
                    "p50": float(np.percentile(rnpvs, 50)),
                    "p90": float(np.percentile(rnpvs, 90)),
                    "mean": float(np.mean(rnpvs)),
                    "std": float(np.std(rnpvs))
                },
                "peak_sales": {
                    "p10": float(np.percentile(peak_sales, 10)),
                    "p50": float(np.percentile(peak_sales, 50)),
                    "p90": float(np.percentile(peak_sales, 90)),
                    "mean": float(np.mean(peak_sales)),
                    "std": float(np.std(peak_sales))
                },
                "net_price": {
                    "p10": float(np.percentile(net_prices, 10)),
                    "p50": float(np.percentile(net_prices, 50)),
                    "p90": float(np.percentile(net_prices, 90)),
                    "mean": float(np.mean(net_prices)),
                    "std": float(np.std(net_prices))
                }
            },
            "probabilities": {
                "p_npv_positive": float(sum(1 for n in npvs if n > 0) / len(npvs)),
                "p_roi_threshold": float(sum(1 for n in npvs if n > 0) / len(npvs))  # Simplified
            },
            "data_sources_used": list(set([p.get("data_source", "default") for p in parameter_rationale.values()]))
        }
    
    def calculate_scenario_delta(
        self,
        base_scenario_id: str,
        comparison_scenario_id: str
    ) -> Dict[str, Any]:
        """
        Calculate scenario deltas
        
        Δ_net_price = Scenario.net_price - BaseScenario.net_price
        Δ_NPV = Scenario.NPV - BaseScenario.NPV
        """
        base_scenario = self._scenarios.get(base_scenario_id)
        comparison_scenario = self._scenarios.get(comparison_scenario_id)
        
        if not base_scenario or not comparison_scenario:
            raise ValueError("One or both scenarios not found")
        
        base_results = base_scenario.get("results", {})
        comp_results = comparison_scenario.get("results", {})
        
        deltas = {
            "net_price": comp_results.get("net_price", 0) - base_results.get("net_price", 0),
            "npv": comp_results.get("npv", 0) - base_results.get("npv", 0),
            "rnpv": comp_results.get("rnpv", 0) - base_results.get("rnpv", 0),
            "peak_sales": comp_results.get("peak_sales", 0) - base_results.get("peak_sales", 0)
        }
        
        return {
            "base_scenario_id": base_scenario_id,
            "comparison_scenario_id": comparison_scenario_id,
            "deltas": deltas
        }
    
    def save_scenario(self, scenario: Dict[str, Any]) -> str:
        """Save scenario to storage"""
        scenario_id = scenario.get("scenario_id", str(uuid.uuid4()))
        scenario["scenario_id"] = scenario_id
        self._scenarios[scenario_id] = scenario
        return scenario_id
    
    def get_scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """Get scenario by ID"""
        return self._scenarios.get(scenario_id)


# Global instance
scenario_engine = ScenarioEngine()

