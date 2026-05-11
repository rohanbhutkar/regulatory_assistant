"""
Price Potential Engine - List-to-Net waterfall calculations and comparator benchmarking
Enhanced with CPP SPU and drug costs data for international pricing
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import numpy as np
import pandas as pd
from scipy import stats
from utils.optimized_data_loader import OptimizedDataLoader
from services.gtn_calculation_service import gtn_calculation_service


class PricePotentialEngine:
    """Service for calculating price potential and net price predictions"""
    
    def __init__(self, data_loader: Optional[OptimizedDataLoader] = None):
        # In-memory storage for price predictions
        self._price_predictions: Dict[str, Dict[str, Any]] = {}
        self._comparator_benchmarks: Dict[str, List[Dict[str, Any]]] = {}
        self.data_loader = data_loader
    
    def get_country_fmv_pricing(self, country: str, procedure_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Get Fair Market Value (FMV) pricing for a country from SPU data
        
        Useful for international market pricing benchmarks
        """
        if not self.data_loader:
            return {}
        
        spu_df = self.data_loader.get_cpp_data('spu')
        if spu_df.empty:
            return {}
        
        # Filter by country (column name may vary)
        country_col = None
        for col in spu_df.columns:
            if 'country' in col.lower() or 'market' in col.lower():
                country_col = col
                break
        
        if country_col:
            country_matches = spu_df[spu_df[country_col].str.contains(country, case=False, na=False)]
            if not country_matches.empty:
                return {
                    "country": country,
                    "records": len(country_matches),
                    "data_source": "cpp_spu",
                    "rationale": f"FMV pricing data from SPU for {country}"
                }
        
        return {}
    
    def get_historical_drug_cost(self, drug_name: str) -> Optional[float]:
        """
        Get historical drug cost from CPP drug costs data
        
        Useful for comparator pricing benchmarks
        """
        if not self.data_loader:
            return None
        
        drug_costs_df = self.data_loader.get_cpp_data('drug_costs')
        if drug_costs_df.empty:
            return None
        
        # Search for drug (fuzzy matching would be ideal)
        for col in drug_costs_df.columns:
            if 'drug' in col.lower() or 'name' in col.lower():
                matches = drug_costs_df[drug_costs_df[col].str.contains(drug_name, case=False, na=False)]
                if not matches.empty:
                    # Get cost column
                    for cost_col in matches.columns:
                        if 'cost' in cost_col.lower() or 'price' in cost_col.lower():
                            cost = matches[cost_col].iloc[0]
                            if pd.notna(cost):
                                return float(cost)
        
        return None
    
    def calculate_waterfall(
        self,
        asset_id: str,
        market: str,
        list_price: float,
        mandatory_discount_pct: float = 0.0,
        expected_rebates: float = 0.0,
        clawbacks: float = 0.0,
        program_adjustments: float = 0.0,
        asset_data: Optional[Dict[str, Any]] = None,
        comparators: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Calculate List-to-Net price waterfall using real data sources when available
        
        Enhanced to use:
        - Formulary tier data for GTN calculations
        - Payer plan data for rebate percentages
        - Comparator data for benchmarking
        
        NetExM = ListExM × (1 − MandatoryDiscount%) − ExpectedRebates − Clawbacks − ProgramAdjustments
        """
        # If we have data loader and asset data, use real GTN calculations
        if self.data_loader and asset_data and market == "US":
            gtn_data = self._calculate_real_gtn_from_data(
                asset_id=asset_id,
                market=market,
                list_price=list_price,
                asset_data=asset_data,
                comparators=comparators
            )
            
            # Use calculated GTN values
            if gtn_data:
                mandatory_discount_pct = gtn_data.get("mandatory_discount_pct", mandatory_discount_pct)
                expected_rebates = gtn_data.get("expected_rebates", expected_rebates)
                clawbacks = gtn_data.get("clawbacks", clawbacks)
                program_adjustments = gtn_data.get("program_adjustments", program_adjustments)
                
                # Store GTN breakdown
                gtn_breakdown = gtn_data.get("gtn_breakdown", {})
                data_sources_used = gtn_data.get("data_sources_used", [])
            else:
                gtn_breakdown = {}
                data_sources_used = []
        else:
            # Fallback to manual inputs
            gtn_breakdown = {}
            data_sources_used = []
        
        # Calculate net price
        net_price = (list_price * (1 - mandatory_discount_pct / 100)) - expected_rebates - clawbacks - program_adjustments
        
        # Calculate GTN percentage
        gtn_percent = ((list_price - net_price) / list_price * 100) if list_price > 0 else 0
        
        waterfall_components = {
            "list_price": list_price,
            "mandatory_discount": {
                "value": list_price * (mandatory_discount_pct / 100),
                "percent": mandatory_discount_pct
            },
            "expected_rebates": expected_rebates,
            "clawbacks": clawbacks,
            "program_adjustments": program_adjustments,
            "net_price": net_price,
            "gtn_percent": gtn_percent,
            "gtn_breakdown": gtn_breakdown,
            "data_sources_used": data_sources_used
        }
        
        # Store prediction
        key = f"{asset_id}_{market}"
        self._price_predictions[key] = {
            "asset_id": asset_id,
            "market": market,
            "list_price": list_price,
            "net_price": net_price,
            "waterfall_components": waterfall_components,
            "calculated_at": datetime.now().isoformat()
        }
        
        return waterfall_components
    
    def predict_net_price_with_uncertainty(
        self,
        asset_id: str,
        market: str,
        list_price: float,
        mandatory_discount_pct: float = 0.0,
        discount_std: float = 2.0,
        rebate_mean: float = 0.0,
        rebate_std: float = 1.0,
        iterations: int = 1000
    ) -> Dict[str, Any]:
        """
        Predict net price with uncertainty using Monte Carlo simulation
        Returns P10, P50, P90 confidence intervals
        """
        # Run Monte Carlo simulation
        net_prices = []
        for _ in range(iterations):
            # Sample from distributions
            sampled_discount = max(0, min(50, np.random.normal(mandatory_discount_pct, discount_std)))
            sampled_rebate = max(0, np.random.normal(rebate_mean, rebate_std))
            
            # Calculate net price
            net_price = (list_price * (1 - sampled_discount / 100)) - sampled_rebate
            net_prices.append(max(0, net_price))  # Ensure non-negative
        
        # Calculate percentiles
        p10 = np.percentile(net_prices, 10)
        p50 = np.percentile(net_prices, 50)
        p90 = np.percentile(net_prices, 90)
        
        # Calculate confidence score based on data completeness
        confidence_score = self._calculate_confidence_score(
            has_discount_data=True,
            has_rebate_data=rebate_mean > 0 or rebate_std > 0
        )
        
        return {
            "net_price_p10": float(p10),
            "net_price_p50": float(p50),
            "net_price_p90": float(p90),
            "net_price_mean": float(np.mean(net_prices)),
            "net_price_std": float(np.std(net_prices)),
            "confidence_score": confidence_score,
            "iterations": iterations
        }
    
    def benchmark_comparators(
        self,
        asset_id: str,
        market: str,
        comparators: List[Dict[str, Any]],
        predicted_net_price: float
    ) -> Dict[str, Any]:
        """
        Benchmark asset price against comparators
        Calculate percentiles and premium/discount
        """
        if not comparators:
            return {
                "comparator_count": 0,
                "percentiles": {},
                "premium_discount": None
            }
        
        # Extract comparator prices
        comparator_prices = [c.get("price", 0) for c in comparators if c.get("price")]
        
        if not comparator_prices:
            return {
                "comparator_count": len(comparators),
                "percentiles": {},
                "premium_discount": None
            }
        
        # Calculate percentiles
        percentiles = {
            "p10": float(np.percentile(comparator_prices, 10)),
            "p25": float(np.percentile(comparator_prices, 25)),
            "p50": float(np.percentile(comparator_prices, 50)),
            "p75": float(np.percentile(comparator_prices, 75)),
            "p90": float(np.percentile(comparator_prices, 90))
        }
        
        # Calculate premium/discount vs median
        median_price = percentiles["p50"]
        premium_discount_pct = ((predicted_net_price - median_price) / median_price * 100) if median_price > 0 else 0
        
        # Store benchmark
        key = f"{asset_id}_{market}"
        self._comparator_benchmarks[key] = comparators
        
        return {
            "comparator_count": len(comparators),
            "percentiles": percentiles,
            "premium_discount": {
                "percent": float(premium_discount_pct),
                "absolute": float(predicted_net_price - median_price)
            },
            "predicted_price": predicted_net_price,
            "median_comparator": median_price
        }
    
    def calculate_subpopulation_price_potential(
        self,
        asset_id: str,
        market: str,
        subpopulations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate price potential by subpopulation
        
        PricePotential_subpop = PredNet_subpop × TreatedPatients_subpop
        TotalPricePotential = Σsubpop PricePotential_subpop
        """
        total_potential = 0.0
        subpop_results = []
        
        for subpop in subpopulations:
            net_price = subpop.get("net_price", 0)
            treated_patients = subpop.get("treated_patients", 0)
            price_potential = net_price * treated_patients
            
            subpop_results.append({
                "subpopulation": subpop.get("name", "Unknown"),
                "net_price": net_price,
                "treated_patients": treated_patients,
                "price_potential": price_potential
            })
            
            total_potential += price_potential
        
        return {
            "subpopulations": subpop_results,
            "total_price_potential": total_potential
        }
    
    def _calculate_confidence_score(
        self,
        has_discount_data: bool,
        has_rebate_data: bool
    ) -> float:
        """Calculate confidence score (0-1) based on data completeness"""
        score = 0.0
        
        if has_discount_data:
            score += 0.5
        if has_rebate_data:
            score += 0.5
        
        return score
    
    def get_price_prediction(self, asset_id: str, market: str) -> Optional[Dict[str, Any]]:
        """Get stored price prediction"""
        key = f"{asset_id}_{market}"
        return self._price_predictions.get(key)
    
    def override_price_component(
        self,
        asset_id: str,
        market: str,
        component_name: str,
        override_value: float,
        justification: str,
        overridden_by: str
    ) -> Dict[str, Any]:
        """Override a price component with justification"""
        key = f"{asset_id}_{market}"
        prediction = self._price_predictions.get(key)
        
        if not prediction:
            raise ValueError(f"No price prediction found for asset {asset_id} in market {market}")
        
        # Store override
        if "overrides" not in prediction:
            prediction["overrides"] = []
        
        prediction["overrides"].append({
            "component_name": component_name,
            "original_value": prediction["waterfall_components"].get(component_name, {}).get("value", 0),
            "override_value": override_value,
            "justification": justification,
            "overridden_by": overridden_by,
            "overridden_at": datetime.now().isoformat()
        })
        
        # Recalculate with override
        # This is simplified - in real implementation, would recalculate waterfall
        self._price_predictions[key] = prediction
        
        return prediction
    
    def _calculate_real_gtn_from_data(
        self,
        asset_id: str,
        market: str,
        list_price: float,
        asset_data: Dict[str, Any],
        comparators: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate real GTN using data sources:
        - Formulary Tier data for tier distribution
        - Payer Plan data for plan coverage
        - Product NDC data for comparator pricing
        - Comparator benchmarks for rebate estimation
        """
        if not self.data_loader:
            return None
        
        data_sources_used = []
        gtn_components = {
            "mandatory_discount_pct": 0.0,
            "expected_rebates": 0.0,
            "clawbacks": 0.0,
            "program_adjustments": 0.0,
            "gtn_breakdown": {},
            "data_sources_used": []
        }
        
        try:
            indication = asset_data.get("indication") or asset_data.get("therapeutic_area", "")
            therapeutic_area = asset_data.get("therapeutic_area", "")
            
            # 1. Get formulary tier data to calculate coverage distribution
            formulary_df = self.data_loader.get_formulary_tier_data()
            if not formulary_df.empty:
                data_sources_used.append("formulary_tier_dim")
                
                # Calculate coverage distribution with restrictions
                gtn_calculation_service.data_loader = self.data_loader
                # Try to get drug name from asset_data for better matching
                drug_name = asset_data.get("asset_name") if asset_data else None
                coverage_distribution = gtn_calculation_service.calculate_coverage_distribution(
                    formulary_df, indication, therapeutic_area, drug_name=drug_name
                )
                
                # Calculate full GTN using top-down rebate method
                gross_sales = list_price  # Using list price as gross sales basis
                full_gtn = gtn_calculation_service.calculate_full_gtn(
                    gross_sales, coverage_distribution, market
                )
                
                # Update GTN components with full calculation
                gtn_components["expected_rebates"] = full_gtn["components"]["rebates"]["amount"]
                gtn_components["gtn_breakdown"]["coverage_distribution"] = coverage_distribution
                gtn_components["gtn_breakdown"]["full_gtn"] = full_gtn
                gtn_components["gtn_breakdown"]["rebate_calculation"] = full_gtn["rebate_calculation"]
                
                # Also include legacy tier distribution for backward compatibility
                tier_distribution = self._estimate_tier_distribution(
                    formulary_df, indication, therapeutic_area
                )
                if tier_distribution:
                    gtn_components["gtn_breakdown"]["tier_distribution"] = tier_distribution
            
            # 2. Get payer plan data to estimate plan coverage and rebates
            # Note: This is now redundant with top-down rebate calculation, but kept for backward compatibility
            # The full_gtn calculation already includes all rebate components
            try:
                payer_plans_df = self.data_loader.get_payer_data("Payer_Plans_Claims_Fact")
                if not payer_plans_df.empty:
                    data_sources_used.append("payer_plans_claims_fact")
                    # Don't override the top-down rebate calculation
                    # Just note that payer plan data was used
            except Exception:
                pass  # Payer plans data may not be available
            
            # 3. Use comparator data to benchmark and adjust rebates
            if comparators:
                data_sources_used.append("comparator_benchmarks")
                comparator_rebate_adjustment = self._adjust_rebates_from_comparators(
                    comparators, list_price, indication
                )
                if comparator_rebate_adjustment != 0:
                    current_rebate = gtn_components["expected_rebates"]
                    gtn_components["expected_rebates"] = max(0, current_rebate + comparator_rebate_adjustment)
                    gtn_components["gtn_breakdown"]["comparator_adjustment"] = comparator_rebate_adjustment
            
            # 4. Estimate mandatory discounts (340B, Medicaid, etc.)
            mandatory_discount_pct = self._estimate_mandatory_discounts(market, therapeutic_area)
            gtn_components["mandatory_discount_pct"] = mandatory_discount_pct
            
            # 5. Estimate clawbacks
            clawback_estimate = self._estimate_clawbacks(therapeutic_area, indication)
            gtn_components["clawbacks"] = clawback_estimate
            
            gtn_components["data_sources_used"] = data_sources_used
            return gtn_components
            
        except Exception:
            # If data-driven calculation fails, return None to use defaults
            return None
    
    def _estimate_tier_distribution(
        self,
        formulary_df: pd.DataFrame,
        indication: str,
        therapeutic_area: str
    ) -> Dict[str, float]:
        """Estimate formulary tier distribution based on indication/therapeutic area"""
        # Default tier distribution
        default_distribution = {
            "Tier 2": 0.20,
            "Tier 3": 0.50,
            "Tier 4": 0.25,
            "Specialty": 0.05
        }
        
        # Try to find similar drugs in formulary data
        if not formulary_df.empty and therapeutic_area:
            for col in formulary_df.columns:
                if 'therapeutic' in col.lower() or 'area' in col.lower():
                    try:
                        matches = formulary_df[
                            formulary_df[col].astype(str).str.contains(
                                therapeutic_area, case=False, na=False
                            )
                        ]
                        if not matches.empty:
                            # Use actual column name: universalstatusrollup
                            tier_col = None
                            if 'universalstatusrollup' in formulary_df.columns:
                                tier_col = 'universalstatusrollup'
                            else:
                                # Fallback: search for tier column
                                for tier_col_name in formulary_df.columns:
                                    if 'tier' in tier_col_name.lower() or 'rollup' in tier_col_name.lower():
                                        tier_col = tier_col_name
                                        break
                            
                            if tier_col:
                                tier_counts = matches[tier_col].value_counts(normalize=True)
                                if not tier_counts.empty:
                                    distribution = {}
                                    for tier, pct in tier_counts.items():
                                        tier_str = str(tier)
                                        # Extract tier number if present (e.g., "Preferred Brand Drugs Tier" -> "Tier 2")
                                        if 'tier' in tier_str.lower():
                                            # Try to extract tier number
                                            import re
                                            tier_match = re.search(r'tier\s*(\d+)', tier_str.lower())
                                            if tier_match:
                                                tier_str = f"Tier {tier_match.group(1)}"
                                        distribution[tier_str] = float(pct)
                                    return distribution
                    except Exception:
                        pass
        
        return default_distribution
    
    def _calculate_weighted_rebate_from_tiers(self, tier_distribution: Dict[str, float]) -> float:
        """Calculate weighted rebate percentage based on tier distribution"""
        tier_rebates = {
            "Tier 2": 15.0,
            "Tier 3": 25.0,
            "Tier 4": 35.0,
            "Specialty": 20.0,
            "Excluded": 0.0
        }
        
        weighted_rebate = 0.0
        for tier, lives_pct in tier_distribution.items():
            rebate_pct = tier_rebates.get(tier, 25.0)
            weighted_rebate += rebate_pct * lives_pct
        
        return weighted_rebate
    
    def _estimate_rebates_from_plans(
        self,
        payer_plans_df: pd.DataFrame,
        indication: str,
        therapeutic_area: str
    ) -> float:
        """Estimate rebate percentage from payer plan claims data"""
        # Simplified: would analyze actual plan rebate patterns
        return 20.0  # 20% baseline rebate
    
    def _adjust_rebates_from_comparators(
        self,
        comparators: List[Dict[str, Any]],
        list_price: float,
        indication: str
    ) -> float:
        """Adjust rebates based on comparator pricing and positioning"""
        if not comparators:
            return 0.0
        
        comparator_prices = [c.get("price", 0) for c in comparators if c.get("price", 0) > 0]
        if not comparator_prices:
            return 0.0
        
        median_comparator = float(np.median(comparator_prices))
        
        if list_price > median_comparator:
            premium_pct = ((list_price - median_comparator) / median_comparator * 100) if median_comparator > 0 else 0
            rebate_adjustment = (premium_pct / 10) * 0.5
            return rebate_adjustment * list_price / 100
        
        return 0.0
    
    def _estimate_mandatory_discounts(self, market: str, therapeutic_area: str) -> float:
        """Estimate mandatory discounts (340B, Medicaid, etc.)"""
        if market != "US":
            return 0.0
        return 7.0  # 7% average mandatory discount
    
    def _estimate_clawbacks(self, therapeutic_area: str, indication: str) -> float:
        """Estimate clawbacks based on therapeutic area and indication"""
        specialty_areas = ["oncology", "rare disease", "gene therapy"]
        if any(area.lower() in therapeutic_area.lower() for area in specialty_areas):
            return 0.02  # 2% of list price
        return 0.01  # 1% of list price


# Global instance
price_potential_engine = PricePotentialEngine()

