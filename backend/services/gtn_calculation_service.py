"""
GTN Calculation Service - Comprehensive Gross-to-Net calculations
Implements top-down rebate forecasting with channel buckets and full GTN components
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import pandas as pd
import numpy as np
from utils.optimized_data_loader import OptimizedDataLoader


class GTNCalculationService:
    """Service for comprehensive GTN calculations with proper coverage levels and channel-based rebates"""
    
    def __init__(self, data_loader: Optional[OptimizedDataLoader] = None):
        self.data_loader = data_loader
    
    def calculate_coverage_distribution(
        self,
        formulary_df: pd.DataFrame,
        indication: str,
        therapeutic_area: str,
        drug_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate coverage distribution with:
        - Coverage level: Unrestricted | Restricted | Not Covered | Not Listed/Unknown
        - Restrictions: PA, ST, QL, or blank if none
        - Percentage for each coverage level
        """
        coverage_distribution = {
            "Unrestricted": {"percentage": 0.0, "restrictions": {}},
            "Restricted": {"percentage": 0.0, "restrictions": {"PA": 0.0, "ST": 0.0, "QL": 0.0}},
            "Not Covered": {"percentage": 0.0, "restrictions": {}},
            "Not Listed/Unknown": {"percentage": 0.0, "restrictions": {}}
        }
        
        if formulary_df.empty:
            # Default distribution if no data
            coverage_distribution["Unrestricted"]["percentage"] = 0.30
            coverage_distribution["Restricted"]["percentage"] = 0.50
            coverage_distribution["Restricted"]["restrictions"]["PA"] = 0.30
            coverage_distribution["Restricted"]["restrictions"]["ST"] = 0.15
            coverage_distribution["Restricted"]["restrictions"]["QL"] = 0.05
            coverage_distribution["Not Covered"]["percentage"] = 0.15
            coverage_distribution["Not Listed/Unknown"]["percentage"] = 0.05
            return coverage_distribution
        
        try:
            # Use actual column names from Formulary_Tier_Dim
            # Columns: universalstatus, universalstatusrollup, pa, st, restrictioncode
            status_col = 'universalstatus' if 'universalstatus' in formulary_df.columns else None
            status_rollup_col = 'universalstatusrollup' if 'universalstatusrollup' in formulary_df.columns else None
            pa_col = 'pa' if 'pa' in formulary_df.columns else None
            st_col = 'st' if 'st' in formulary_df.columns else None
            restriction_code_col = 'restrictioncode' if 'restrictioncode' in formulary_df.columns else None
            
            # Filter by therapeutic area if available
            # Use actual column name: therapeuticclass
            filtered_df = formulary_df
            if therapeutic_area:
                therapeutic_col = None
                if 'therapeuticclass' in formulary_df.columns:
                    therapeutic_col = 'therapeuticclass'
                elif 'indicationname' in formulary_df.columns:
                    therapeutic_col = 'indicationname'
                else:
                    # Fallback: search for therapeutic/area column
                    for col in formulary_df.columns:
                        if 'therapeutic' in col.lower() or 'area' in col.lower() or 'indication' in col.lower():
                            therapeutic_col = col
                            break
                
                if therapeutic_col:
                    try:
                        filtered_df = formulary_df[
                            formulary_df[therapeutic_col].astype(str).str.contains(
                                therapeutic_area, case=False, na=False
                            )
                        ]
                    except Exception:
                        pass
            
            if not filtered_df.empty:
                # Calculate coverage distribution using actual column names
                total = len(filtered_df)
                if total > 0:
                    # Use universalstatus or universalstatusrollup to determine coverage
                    status_col_to_use = status_col or status_rollup_col
                    
                    if status_col_to_use and status_col_to_use in filtered_df.columns:
                        # Count by coverage status
                        status_counts = filtered_df[status_col_to_use].value_counts()
                        
                        # Map to coverage levels
                        for status, count in status_counts.items():
                            pct = count / total
                            status_str = str(status).lower()
                            
                            if 'preferred' in status_str or ('covered' in status_str and 'not' not in status_str and 'non' not in status_str):
                                coverage_distribution["Unrestricted"]["percentage"] += pct
                            elif 'non-preferred' in status_str or 'restricted' in status_str or 'non preferred' in status_str:
                                coverage_distribution["Restricted"]["percentage"] += pct
                            elif 'not covered' in status_str or 'excluded' in status_str:
                                coverage_distribution["Not Covered"]["percentage"] += pct
                            else:
                                coverage_distribution["Not Listed/Unknown"]["percentage"] += pct
                        
                        # Calculate restriction percentages within Restricted category
                        if coverage_distribution["Restricted"]["percentage"] > 0:
                            restricted_df = filtered_df[
                                filtered_df[status_col_to_use].astype(str).str.contains('non-preferred|restricted|non preferred', case=False, na=False, regex=True)
                            ]
                            if restricted_df.empty:
                                # Also check for any non-preferred/restricted status
                                restricted_df = filtered_df[
                                    ~filtered_df[status_col_to_use].astype(str).str.contains('preferred|covered', case=False, na=False, regex=True)
                                ]
                            
                            if not restricted_df.empty:
                                total_restricted = len(restricted_df)
                                
                                # Count PA restrictions
                                if pa_col and pa_col in restricted_df.columns:
                                    pa_count = restricted_df[pa_col].notna().sum()
                                    pa_non_empty = restricted_df[pa_col].astype(str).str.strip().ne('').sum()
                                    coverage_distribution["Restricted"]["restrictions"]["PA"] = (
                                        max(pa_count, pa_non_empty) / total_restricted if total_restricted > 0 else 0.0
                                    )
                                
                                # Count ST restrictions
                                if st_col and st_col in restricted_df.columns:
                                    st_count = restricted_df[st_col].notna().sum()
                                    st_non_empty = restricted_df[st_col].astype(str).str.strip().ne('').sum()
                                    coverage_distribution["Restricted"]["restrictions"]["ST"] = (
                                        max(st_count, st_non_empty) / total_restricted if total_restricted > 0 else 0.0
                                    )
                                
                                # Count QL restrictions from restrictioncode
                                if restriction_code_col and restriction_code_col in restricted_df.columns:
                                    ql_count = restricted_df[restriction_code_col].astype(str).str.contains('ql|quantity', case=False, na=False, regex=True).sum()
                                    coverage_distribution["Restricted"]["restrictions"]["QL"] = (
                                        ql_count / total_restricted if total_restricted > 0 else 0.0
                                    )
                    else:
                        # No status column found, use defaults
                        print("⚠️ No status column (universalstatus/universalstatusrollup) found in formulary data, using default distribution")
                        coverage_distribution["Unrestricted"]["percentage"] = 0.30
                        coverage_distribution["Restricted"]["percentage"] = 0.50
                        coverage_distribution["Restricted"]["restrictions"]["PA"] = 0.30
                        coverage_distribution["Restricted"]["restrictions"]["ST"] = 0.15
                        coverage_distribution["Restricted"]["restrictions"]["QL"] = 0.05
                        coverage_distribution["Not Covered"]["percentage"] = 0.15
                        coverage_distribution["Not Listed/Unknown"]["percentage"] = 0.05
            else:
                # No filtered data, use defaults
                print("⚠️ No formulary data matches therapeutic area, using default distribution")
                coverage_distribution["Unrestricted"]["percentage"] = 0.30
                coverage_distribution["Restricted"]["percentage"] = 0.50
                coverage_distribution["Restricted"]["restrictions"]["PA"] = 0.30
                coverage_distribution["Restricted"]["restrictions"]["ST"] = 0.15
                coverage_distribution["Restricted"]["restrictions"]["QL"] = 0.05
                coverage_distribution["Not Covered"]["percentage"] = 0.15
                coverage_distribution["Not Listed/Unknown"]["percentage"] = 0.05
        except Exception as e:
            print(f"⚠️ Error calculating coverage distribution: {e}")
            import traceback
            traceback.print_exc()
            # Return default if error
            coverage_distribution["Unrestricted"]["percentage"] = 0.30
            coverage_distribution["Restricted"]["percentage"] = 0.50
            coverage_distribution["Restricted"]["restrictions"]["PA"] = 0.30
            coverage_distribution["Restricted"]["restrictions"]["ST"] = 0.15
            coverage_distribution["Restricted"]["restrictions"]["QL"] = 0.05
            coverage_distribution["Not Covered"]["percentage"] = 0.15
            coverage_distribution["Not Listed/Unknown"]["percentage"] = 0.05
        
        # Ensure percentages sum to 1.0
        total_pct = sum([v["percentage"] for v in coverage_distribution.values()])
        if total_pct == 0.0:
            # All zeros, use defaults
            coverage_distribution["Unrestricted"]["percentage"] = 0.30
            coverage_distribution["Restricted"]["percentage"] = 0.50
            coverage_distribution["Restricted"]["restrictions"]["PA"] = 0.30
            coverage_distribution["Restricted"]["restrictions"]["ST"] = 0.15
            coverage_distribution["Restricted"]["restrictions"]["QL"] = 0.05
            coverage_distribution["Not Covered"]["percentage"] = 0.15
            coverage_distribution["Not Listed/Unknown"]["percentage"] = 0.05
        elif total_pct != 1.0:
            # Normalize to sum to 1.0
            for key in coverage_distribution:
                coverage_distribution[key]["percentage"] /= total_pct
        
        return coverage_distribution
    
    def calculate_top_down_rebates(
        self,
        gross_sales: float,
        coverage_distribution: Dict[str, Any],
        market: str = "US"
    ) -> Dict[str, Any]:
        """
        Calculate top-down rebates using channel buckets:
        - Commercial (PBM/plan rebates)
        - Medicare Part D (negotiated rebates + MDP)
        - Medicaid (MDRP)
        - Federal/Other Gov (VA/DoD/TRICARE)
        - 340B (chargebacks)
        
        Formula: Total Rebates = Σ (Gross Sales × Channel Mix × Effective Rebate %)
        """
        if market != "US":
            return {
                "total_rebates": 0.0,
                "channel_breakdown": {},
                "effective_rebate_pct": 0.0
            }
        
        # Default channel mix (would be data-driven in production)
        channel_mix = {
            "Commercial": 0.55,      # 55% of gross sales
            "Medicare Part D": 0.25,  # 25% of gross sales
            "Medicaid": 0.10,          # 10% of gross sales
            "Federal/Other Gov": 0.05, # 5% of gross sales
            "340B": 0.05              # 5% of gross sales
        }
        
        # Effective rebate rates by channel (would be calibrated from historical data)
        effective_rebate_rates = {
            "Commercial": self._calculate_commercial_rebate_rate(coverage_distribution),
            "Medicare Part D": self._calculate_medicare_part_d_rebate_rate(),
            "Medicaid": self._calculate_medicaid_rebate_rate(),
            "Federal/Other Gov": 0.24,  # 24% typical for VA/DoD
            "340B": 0.0  # 340B is chargebacks, not rebates
        }
        
        # Calculate rebates by channel
        channel_breakdown = {}
        total_rebates = 0.0
        
        for channel, mix_pct in channel_mix.items():
            channel_gross = gross_sales * mix_pct
            rebate_rate = effective_rebate_rates[channel]
            channel_rebates = channel_gross * (rebate_rate / 100)
            
            channel_breakdown[channel] = {
                "gross_sales": channel_gross,
                "mix_percentage": mix_pct * 100,
                "effective_rebate_rate": rebate_rate,
                "rebates": channel_rebates
            }
            
            total_rebates += channel_rebates
        
        effective_rebate_pct = (total_rebates / gross_sales * 100) if gross_sales > 0 else 0.0
        
        return {
            "total_rebates": total_rebates,
            "channel_breakdown": channel_breakdown,
            "effective_rebate_pct": effective_rebate_pct,
            "channel_mix": channel_mix
        }
    
    def _calculate_commercial_rebate_rate(self, coverage_distribution: Dict[str, Any]) -> float:
        """Calculate commercial rebate rate based on coverage/access position"""
        # Base rebate rates by coverage level
        base_rates = {
            "Unrestricted": 15.0,      # 15% for unrestricted access
            "Restricted": 25.0,        # 25% for restricted access
            "Not Covered": 0.0,        # No rebates if not covered
            "Not Listed/Unknown": 20.0 # 20% for unknown/not listed
        }
        
        # Calculate weighted average
        weighted_rate = 0.0
        for coverage_level, data in coverage_distribution.items():
            pct = data.get("percentage", 0.0)
            base_rate = base_rates.get(coverage_level, 20.0)
            
            # Adjust for restrictions (higher rebates needed for PA/ST)
            if coverage_level == "Restricted":
                restrictions = data.get("restrictions", {})
                pa_pct = restrictions.get("PA", 0.0)
                st_pct = restrictions.get("ST", 0.0)
                # Increase rebate rate for restricted access
                adjustment = (pa_pct * 5.0) + (st_pct * 3.0)  # Additional % for PA/ST
                base_rate += adjustment
            
            weighted_rate += base_rate * pct
        
        return weighted_rate
    
    def _calculate_medicare_part_d_rebate_rate(self) -> float:
        """
        Calculate Medicare Part D rebate rate including:
        - Negotiated rebates (similar to commercial)
        - Manufacturer Discount Program (MDP) for 2025+
        """
        # Negotiated rebates (typically 15-20%)
        negotiated_rebate = 18.0
        
        # MDP discount (typically 20% in catastrophic phase, 10% in initial coverage)
        # Weighted average assuming 60% initial, 40% catastrophic
        mdp_discount = (0.6 * 10.0) + (0.4 * 20.0)  # 14% average
        
        # Total Part D rebate rate
        return negotiated_rebate + mdp_discount
    
    def _calculate_medicaid_rebate_rate(self) -> float:
        """
        Calculate Medicaid rebate rate (MDRP):
        - Basic rebate: greater of 23.1% of AMP or (AMP - Best Price)
        - Inflation penalty (if applicable)
        - No cap on total rebates (post-2024)
        """
        # Base rebate rate (typically 23.1% minimum, can be higher)
        base_rebate = 23.1
        
        # Inflation penalty adjustment (if applicable)
        inflation_penalty = 2.0  # Additional 2% for inflation penalty
        
        return base_rebate + inflation_penalty
    
    def calculate_full_gtn(
        self,
        gross_sales: float,
        coverage_distribution: Dict[str, Any],
        market: str = "US"
    ) -> Dict[str, Any]:
        """
        Calculate full GTN including all components:
        - Rebates (commercial/PBM, Medicare Part D, Medicaid, etc.)
        - Chargebacks (wholesaler discounts, 340B)
        - Cash/prompt-pay discounts
        - Returns (and return reserves)
        - Fees (distribution/service/admin fees, GPO/admin)
        - Other price concessions (price protection, shelf stock adjustments)
        - Patient assistance/copay programs
        """
        # Calculate rebates using top-down method
        rebate_calc = self.calculate_top_down_rebates(gross_sales, coverage_distribution, market)
        total_rebates = rebate_calc["total_rebates"]
        
        # Chargebacks (typically 2-5% of gross, includes 340B)
        chargeback_rate = 0.035  # 3.5% of gross sales
        chargebacks = gross_sales * chargeback_rate
        
        # Cash/prompt-pay discounts (typically 1-2% of gross)
        cash_discount_rate = 0.015  # 1.5% of gross sales
        cash_discounts = gross_sales * cash_discount_rate
        
        # Returns and return reserves (typically 0.5-1% of gross)
        returns_rate = 0.0075  # 0.75% of gross sales
        returns = gross_sales * returns_rate
        
        # Fees (distribution/service/admin fees, typically 1-2% of gross)
        fees_rate = 0.015  # 1.5% of gross sales
        fees = gross_sales * fees_rate
        
        # Other price concessions (price protection, shelf stock adjustments, typically 0.5-1%)
        other_concessions_rate = 0.0075  # 0.75% of gross sales
        other_concessions = gross_sales * other_concessions_rate
        
        # Patient assistance/copay programs (typically 2-5% of gross for specialty drugs)
        patient_assistance_rate = 0.03  # 3% of gross sales
        patient_assistance = gross_sales * patient_assistance_rate
        
        # Calculate total GTN
        total_gtn = (
            total_rebates +
            chargebacks +
            cash_discounts +
            returns +
            fees +
            other_concessions +
            patient_assistance
        )
        
        gtn_percent = (total_gtn / gross_sales * 100) if gross_sales > 0 else 0.0
        net_sales = gross_sales - total_gtn
        
        return {
            "gross_sales": gross_sales,
            "net_sales": net_sales,
            "total_gtn": total_gtn,
            "gtn_percent": gtn_percent,
            "components": {
                "rebates": {
                    "amount": total_rebates,
                    "percent": (total_rebates / gross_sales * 100) if gross_sales > 0 else 0.0,
                    "breakdown": rebate_calc["channel_breakdown"]
                },
                "chargebacks": {
                    "amount": chargebacks,
                    "percent": chargeback_rate * 100
                },
                "cash_discounts": {
                    "amount": cash_discounts,
                    "percent": cash_discount_rate * 100
                },
                "returns": {
                    "amount": returns,
                    "percent": returns_rate * 100
                },
                "fees": {
                    "amount": fees,
                    "percent": fees_rate * 100
                },
                "other_concessions": {
                    "amount": other_concessions,
                    "percent": other_concessions_rate * 100
                },
                "patient_assistance": {
                    "amount": patient_assistance,
                    "percent": patient_assistance_rate * 100
                }
            },
            "coverage_distribution": coverage_distribution,
            "rebate_calculation": rebate_calc
        }


# Global instance
gtn_calculation_service = GTNCalculationService()
