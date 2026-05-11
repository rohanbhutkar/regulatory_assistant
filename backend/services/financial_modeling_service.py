"""
Financial Modeling Service - Patient funnel, revenue, GTN, NPV/ROI calculations
Enhanced with data-driven patient funnel from claims data
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
import numpy as np
from utils.optimized_data_loader import OptimizedDataLoader


class FinancialModelingService:
    """Service for financial modeling and value calculations"""
    
    def __init__(self, data_loader: Optional[OptimizedDataLoader] = None):
        # In-memory storage
        self._patient_funnels: Dict[str, Dict[str, Any]] = {}
        self._revenue_projections: Dict[str, Dict[str, Any]] = {}
        self._financial_projections: Dict[str, Dict[str, Any]] = {}
        self._roi_curves: Dict[str, Dict[str, Any]] = {}
        self.data_loader = data_loader
    
    def calculate_patient_funnel(
        self,
        asset_id: str,
        market: str,
        prevalence: Optional[float] = None,
        indication: Optional[str] = None,
        diagnosis_rate: float = 0.7,
        eligibility_rate: Optional[float] = None,
        access_rate: Optional[float] = None,
        uptake_rate: float = 0.6,
        market_share: float = 0.1,
        subpopulations: Optional[List[Dict[str, Any]]] = None,
        data_loader: Optional[OptimizedDataLoader] = None,
        # Integration parameters
        coverage_data: Optional[Dict[str, Any]] = None,
        hta_outcome: Optional[str] = None,
        tier_distribution: Optional[Dict[str, float]] = None,
        hta_access_risk: Optional[Dict[str, Any]] = None,
        asset_data: Optional[Dict[str, Any]] = None,
        comparators: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Calculate patient funnel from indications using claims data
        
        Enhanced with integrations:
        - Coverage data → access_rate
        - HTA outcome → eligibility_rate
        - Tier distribution → weighted access_rate
        - HTA access risk → uncertainty adjustments
        
        Eligible = Prevalence × DiagnosisRate × EligibilityRate(subpop)
        Treated = Eligible × AccessRate × UptakeRate(t) × MarketShare(t)
        Units = Treated × DosingUnitsPerPatientPerYear
        """
        # If indication provided and data loader available, calculate prevalence from claims
        loader = data_loader or self.data_loader
        prevalence_calculation_details = None
        if indication and loader and market == "US":
            prevalence_data = self._calculate_prevalence_from_claims(loader, indication)
            if prevalence_data and prevalence_data.get("prevalence"):
                prevalence = prevalence_data["prevalence"]
                prevalence_calculation_details = prevalence_data.get("calculation_details")
        
        # Use provided prevalence or default
        if prevalence is None:
            prevalence = 0.01  # 1% default if not calculated
        
        # INTEGRATION 1: HTA Outcome → Eligibility Rate
        if eligibility_rate is None:
            if hta_outcome == "rejection":
                eligibility_rate = 0.0  # No eligibility if HTA rejects
            elif hta_outcome == "restriction":
                eligibility_rate = 0.3  # Reduced eligibility for restrictions
            elif hta_outcome == "approval":
                eligibility_rate = 0.5  # Normal eligibility
            else:
                eligibility_rate = 0.5  # Default
        else:
            # If HTA outcome provided, adjust provided rate
            if hta_outcome == "rejection":
                eligibility_rate = 0.0
            elif hta_outcome == "restriction":
                eligibility_rate *= 0.6  # Reduce by 40%
        
        # INTEGRATION 2: Coverage Level → Access Rate
        if access_rate is None:
            if coverage_data:
                coverage_level = coverage_data.get("coverage_level", "Unknown")
                if coverage_level == "Not Covered":
                    access_rate = 0.0
                elif coverage_level == "Restricted":
                    # Check restrictions
                    restrictions = coverage_data.get("restrictions", [])
                    restriction_penalty = len(restrictions) * 0.15  # 15% per restriction
                    access_rate = max(0.0, 0.6 - restriction_penalty)
                elif coverage_level == "Unrestricted":
                    access_rate = 0.85
                else:
                    access_rate = 0.5  # Unknown/Not Listed - conservative
            else:
                access_rate = 0.8  # Default if no coverage data
        
        # INTEGRATION 3: Tier Distribution → Weighted Access Rate
        if tier_distribution and access_rate > 0:
            # Calculate weighted access rate based on tier distribution
            tier_access_rates = {
                "Tier 1": 0.95,
                "Tier 2": 0.85,
                "Tier 3": 0.70,
                "Tier 4": 0.50,
                "Specialty": 0.60,
                "Excluded": 0.0,
                "Not Covered": 0.0,
                "Not Listed/Unknown": 0.3
            }
            
            weighted_access = 0.0
            total_lives = sum(tier_distribution.values())
            
            if total_lives > 0:
                for tier, lives_pct in tier_distribution.items():
                    tier_access = tier_access_rates.get(tier, 0.5)
                    weighted_access += tier_access * lives_pct
                
                # Blend tier-based access with coverage-based access
                access_rate = (weighted_access * 0.7) + (access_rate * 0.3)
        
        # INTEGRATION 4: HTA Access Risk → Uncertainty Adjustment
        access_risk_adjustment = 1.0
        if hta_access_risk:
            risk_score = hta_access_risk.get("access_risk_score", 50)  # 0-100
            # High risk (70+) reduces access by up to 20%
            if risk_score >= 70:
                access_risk_adjustment = 0.8
            elif risk_score >= 50:
                access_risk_adjustment = 0.9
            # Low risk (<30) increases access by up to 10%
            elif risk_score < 30:
                access_risk_adjustment = 1.1
            
            access_rate *= access_risk_adjustment
            access_rate = min(1.0, max(0.0, access_rate))  # Clamp to 0-1
        
        # INTEGRATION 5: Competitor Timeline → Market Share (time-varying)
        # This will be handled in revenue calculation, but store base market share
        base_market_share = market_share
        if comparators:
            # Adjust initial market share based on number of competitors
            competitor_count = len([c for c in comparators if c.get("launch_date")])
            if competitor_count > 0:
                # More competitors = lower market share
                market_share = market_share / (1 + competitor_count * 0.1)
        
        # Base funnel calculation
        diagnosed = prevalence * diagnosis_rate
        eligible = diagnosed * eligibility_rate
        accessible = eligible * access_rate
        treated = accessible * uptake_rate
        units = treated * market_share  # Simplified - would multiply by dosing units
        
        funnel = {
            "asset_id": asset_id,
            "market": market,
            "indication": indication,
            "prevalence": prevalence,
            "prevalence_source": "claims_data" if indication and loader and prevalence_calculation_details else "manual",
            "prevalence_calculation_details": prevalence_calculation_details,
            "diagnosed": diagnosed,
            "eligible": eligible,
            "accessible": accessible,
            "treated": treated,
            "units": units,
            "market_share": market_share,
            "base_market_share": base_market_share,
            "funnel_stages": [
                {"stage": "Prevalence", "count": prevalence, "conversion_rate": 1.0},
                {"stage": "Diagnosed", "count": diagnosed, "conversion_rate": diagnosis_rate},
                {"stage": "Eligible", "count": eligible, "conversion_rate": eligibility_rate},
                {"stage": "Accessible", "count": accessible, "conversion_rate": access_rate},
                {"stage": "Treated", "count": treated, "conversion_rate": uptake_rate},
                {"stage": "Market Share", "count": units, "conversion_rate": market_share}
            ],
            "integration_details": {
                "coverage_level": coverage_data.get("coverage_level") if coverage_data else None,
                "hta_outcome": hta_outcome,
                "tier_distribution_used": tier_distribution is not None,
                "access_risk_score": hta_access_risk.get("access_risk_score") if hta_access_risk else None,
                "access_risk_adjustment": access_risk_adjustment,
                "competitor_count": len(comparators) if comparators else 0,
                "calculated_access_rate": access_rate,
                "calculated_eligibility_rate": eligibility_rate
            },
            "calculated_at": datetime.now().isoformat()
        }
        
        # Handle subpopulations
        if subpopulations:
            subpop_results = []
            total_units = 0
            for subpop in subpopulations:
                subpop_prevalence = subpop.get("prevalence", prevalence)
                subpop_eligibility = subpop.get("eligibility_rate", eligibility_rate)
                
                subpop_eligible = subpop_prevalence * diagnosis_rate * subpop_eligibility
                subpop_treated = subpop_eligible * access_rate * uptake_rate * market_share
                subpop_units = subpop_treated
                
                subpop_results.append({
                    "subpopulation": subpop.get("name", "Unknown"),
                    "prevalence": subpop_prevalence,
                    "eligible": subpop_eligible,
                    "treated": subpop_treated,
                    "units": subpop_units
                })
                total_units += subpop_units
            
            funnel["subpopulations"] = subpop_results
            funnel["total_units"] = total_units
        
        # Store
        key = f"{asset_id}_{market}"
        self._patient_funnels[key] = funnel
        
        return funnel
    
    def calculate_revenue(
        self,
        asset_id: str,
        market: str,
        net_price: float,
        units: float,
        years: int = 10,
        launch_date: Optional[str] = None,
        peak_sales_year: int = 3,  # Years from launch to peak
        # Integration parameters
        time_to_reimbursement_months: Optional[int] = None,
        key_milestone_dates: Optional[Dict[str, str]] = None,
        comparators: Optional[List[Dict[str, Any]]] = None,
        base_market_share: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate revenue trajectory using S-curve (sigmoid) model
        
        Uses sigmoid function for realistic S-curve growth:
        Revenue(t) = PeakSales / (1 + e^(-k*(t - t0)))
        Where:
        - PeakSales = NetPrice × Units × PeakMultiplier
        - k = growth rate (steepness of curve)
        - t0 = time to peak (inflection point)
        - t = years from launch
        
        GrossSales = ListPrice × Units
        NetSales = NetPrice × Units
        """
        
        # Calculate base annual revenue
        gross_sales = net_price * 1.2 * units  # Assume 20% list premium
        net_sales = net_price * units
        peak_sales_value = net_sales * 1.5  # Peak at 150% of initial (accounts for market growth)
        
        # INTEGRATION 2: HTA Time-to-Reimbursement → Revenue Start Date
        # Revenue should start at launch + reimbursement delay
        reimbursement_delay_months = 0
        if time_to_reimbursement_months:
            reimbursement_delay_months = time_to_reimbursement_months
        elif key_milestone_dates:
            # Try to calculate from milestone dates
            try:
                approval_date = key_milestone_dates.get("FDA Approval") or key_milestone_dates.get("EMA Approval")
                reimbursement_date = key_milestone_dates.get("Reimbursement") or key_milestone_dates.get("HTA Decision")
                if approval_date and reimbursement_date:
                    approval_dt = datetime.fromisoformat(approval_date.replace('Z', '+00:00'))
                    reimbursement_dt = datetime.fromisoformat(reimbursement_date.replace('Z', '+00:00'))
                    reimbursement_delay_months = int((reimbursement_dt - approval_dt).days / 30)
            except Exception:
                pass
        
        # Determine launch date
        if launch_date:
            try:
                if isinstance(launch_date, str):
                    launch_dt = datetime.fromisoformat(launch_date.replace('Z', '+00:00'))
                else:
                    launch_dt = launch_date
                launch_year = launch_dt.year
                launch_month = launch_dt.month
            except Exception:
                launch_year = datetime.now().year
                launch_month = datetime.now().month
        else:
            launch_year = datetime.now().year
            launch_month = datetime.now().month
        
        # Revenue start date = launch + reimbursement delay
        revenue_start_year = launch_year
        revenue_start_month = launch_month + reimbursement_delay_months
        while revenue_start_month > 12:
            revenue_start_month -= 12
            revenue_start_year += 1
        
        # INTEGRATION 6: Competitor Timeline → Market Share Erosion
        # Market share should erode over time as competitors launch
        competitor_launch_dates = []
        if comparators:
            for comp in comparators:
                comp_launch = comp.get("launch_date")
                if comp_launch:
                    try:
                        if isinstance(comp_launch, str):
                            comp_dt = datetime.fromisoformat(comp_launch.replace('Z', '+00:00'))
                        else:
                            comp_dt = comp_launch
                        competitor_launch_dates.append(comp_dt)
                    except Exception:
                        pass
        
        # S-curve parameters
        # k controls steepness: higher k = steeper curve
        # Typical pharmaceutical uptake: k = 0.8-1.2
        k = 1.0  # Growth rate parameter
        t0 = peak_sales_year  # Inflection point (years to peak)
        
        # INTEGRATION 7: Timeline Milestones → Revenue Phases
        # Determine revenue phases based on milestones
        phases = {
            "pre_launch": True,  # Before launch
            "launch": True,  # At launch
            "reimbursement": reimbursement_delay_months > 0,  # After reimbursement
            "full_access": True  # Full market access
        }
        
        # Generate monthly trajectory for smoother S-curve
        revenue_trajectory = []
        months_from_launch = 0
        
        # Calculate for years * 12 months
        total_months = years * 12
        
        # Use base market share if provided, otherwise use current units-based share
        current_market_share = base_market_share if base_market_share is not None else (units / (prevalence * 0.7 * 0.5 * 0.8 * 0.6) if prevalence > 0 else 0.1)
        
        # Create launch datetime for competitor calculations
        try:
            if launch_date:
                if isinstance(launch_date, str):
                    launch_dt = datetime.fromisoformat(launch_date.replace('Z', '+00:00'))
                else:
                    launch_dt = launch_date
            else:
                launch_dt = datetime(launch_year, launch_month, 1)
        except Exception:
            launch_dt = datetime(launch_year, launch_month, 1)
        
        for month in range(total_months):
            months_from_launch = month
            years_from_launch = months_from_launch / 12.0
            
            # INTEGRATION 6: Apply market share erosion from competitors
            market_share_erosion = 1.0
            if competitor_launch_dates and current_market_share:
                current_date = launch_dt + timedelta(days=month * 30)
                for comp_launch in competitor_launch_dates:
                    if current_date >= comp_launch:
                        # Competitor has launched - erode market share
                        months_since_comp_launch = (current_date - comp_launch).days / 30
                        # Erode 2% per month for first 12 months, then 1% per month
                        if months_since_comp_launch <= 12:
                            erosion = 0.02 * months_since_comp_launch
                        else:
                            erosion = 0.24 + 0.01 * (months_since_comp_launch - 12)
                        market_share_erosion *= (1 - min(erosion, 0.5))  # Max 50% erosion per competitor
                
                # Apply erosion to units
                eroded_units = units * market_share_erosion
            else:
                eroded_units = units
            
            # INTEGRATION 7: Apply phase-based revenue model
            # Pre-launch: No revenue
            if month == 0 and reimbursement_delay_months > 0:
                # Before reimbursement, revenue is limited
                revenue_multiplier = 0.3  # 30% of potential during reimbursement delay
            elif months_from_launch < reimbursement_delay_months:
                # During reimbursement delay, ramp up slowly
                ramp_up = months_from_launch / max(reimbursement_delay_months, 1)
                revenue_multiplier = 0.3 + (0.7 * ramp_up)  # Ramp from 30% to 100%
            else:
                revenue_multiplier = 1.0
            
            # S-curve calculation using sigmoid function
            # Sigmoid: 1 / (1 + e^(-k*(t - t0)))
            # We want it to start at 0 and reach peak_sales_value
            sigmoid_value = 1 / (1 + np.exp(-k * (years_from_launch - t0)))
            
            # Apply S-curve to revenue
            # Start at 0, grow to peak, then apply erosion after peak
            if years_from_launch < t0:
                # Growth phase: use sigmoid
                revenue = peak_sales_value * sigmoid_value * revenue_multiplier
            else:
                # After peak: apply erosion (exponential decay)
                years_past_peak = years_from_launch - t0
                erosion_rate = 0.05  # 5% erosion per year after peak
                peak_revenue = peak_sales_value * (1 / (1 + np.exp(-k * (t0 - t0))))  # Peak value
                revenue = peak_revenue * np.exp(-erosion_rate * years_past_peak) * revenue_multiplier
            
            # Apply market share erosion from competitors
            revenue *= market_share_erosion
            
            # Calculate calendar year and month (from revenue start, not launch)
            total_months_from_revenue_start = revenue_start_month - 1 + month
            calendar_year = revenue_start_year + (total_months_from_revenue_start // 12)
            calendar_month = (total_months_from_revenue_start % 12) + 1
            
            # Only add annual data points (every 12 months) for cleaner chart
            if month % 12 == 0:
                # Calculate units for this point based on revenue
                current_units = eroded_units if 'eroded_units' in locals() else units
                if net_sales > 0 and revenue > 0:
                    # Scale units proportionally to revenue
                    revenue_ratio = revenue / (peak_sales_value * revenue_multiplier * market_share_erosion) if (peak_sales_value * revenue_multiplier * market_share_erosion) > 0 else 1.0
                    current_units = current_units * revenue_ratio
                
                revenue_trajectory.append({
                    "year": calendar_year,
                    "year_label": f"{calendar_year}",
                    "months_from_launch": months_from_launch,
                    "years_from_launch": round(years_from_launch, 1),
                    "revenue": max(0, float(revenue)),
                    "units": max(0, float(current_units)),
                    "market_share_erosion": market_share_erosion,
                    "revenue_phase": "pre_reimbursement" if months_from_launch < reimbursement_delay_months else "post_reimbursement"
                })
        
        # Annual revenue summary
        annual_revenue = {
            "gross_sales": gross_sales,
            "net_sales": net_sales,
            "units": units
        }
        
        # Find peak sales and time to peak
        peak_revenue_entry = max(revenue_trajectory, key=lambda x: x["revenue"])
        peak_sales = peak_revenue_entry["revenue"]
        time_to_peak_years = peak_revenue_entry["years_from_launch"]
        
        result = {
            "asset_id": asset_id,
            "market": market,
            "annual_revenue": annual_revenue,
            "revenue_trajectory": revenue_trajectory,
            "peak_sales": peak_sales,
            "time_to_peak_years": time_to_peak_years,
            "launch_date": launch_date or f"{launch_year}-{launch_month:02d}-01",
            "revenue_start_date": f"{revenue_start_year}-{revenue_start_month:02d}-01",
            "launch_year": launch_year,
            "reimbursement_delay_months": reimbursement_delay_months,
            "calculation_method": "S-curve (sigmoid) with integrations",
            "integration_details": {
                "time_to_reimbursement_months": time_to_reimbursement_months,
                "competitor_count": len(competitor_launch_dates),
                "market_share_erosion_applied": len(competitor_launch_dates) > 0,
                "revenue_phases_used": phases
            },
            "calculated_at": datetime.now().isoformat()
        }
        
        # Store
        key = f"{asset_id}_{market}"
        self._revenue_projections[key] = result
        
        return result
    
    def calculate_gtn(
        self,
        asset_id: str,
        market: str,
        list_price: float,
        mandatory_discount_pct: float = 0.0,
        voluntary_rebate_pct: float = 0.0,
        clawback_pct: float = 0.0,
        program_adjustments: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculate GTN (Gross-to-Net) for international markets
        
        NetPrice = ListExM − Σ(GTN_components_per_unit)
        GTN% = 1 − (NetPrice / ListExM)
        """
        mandatory_discount = list_price * (mandatory_discount_pct / 100)
        voluntary_rebate = list_price * (voluntary_rebate_pct / 100)
        clawback = list_price * (clawback_pct / 100)
        
        net_price = list_price - mandatory_discount - voluntary_rebate - clawback - program_adjustments
        gtn_percent = ((list_price - net_price) / list_price * 100) if list_price > 0 else 0
        
        return {
            "asset_id": asset_id,
            "market": market,
            "list_price": list_price,
            "mandatory_discount": mandatory_discount,
            "voluntary_rebate": voluntary_rebate,
            "clawback": clawback,
            "program_adjustments": program_adjustments,
            "net_price": net_price,
            "gtn_percent": gtn_percent,
            "calculated_at": datetime.now().isoformat()
        }
    
    def calculate_us_gtn(
        self,
        asset_id: str,
        wac: float,
        tier_distribution: Dict[str, float],
        access_scores: Dict[str, float],
        channel: str = "commercial"
    ) -> Dict[str, Any]:
        """
        Calculate US GTN with formulary tiering
        
        AccessScore_plan = BaseTierScore(tier) − UM_Penalty(PA/ST/QL) + PreferredBonus − ExclusionPenalty
        ExpectedRebate%_plan = f_channel(AccessScore_plan, CompetitorPosition, PriceAggressiveness)
        Rebate%_channel = (Σplans Lives_plan × ExpectedRebate%_plan) / (Σplans Lives_plan)
        NetPrice_channel = WAC × (1 − Rebate%_channel) − Fees − Chargebacks
        """
        # Base tier scores
        tier_scores = {
            "Tier 2": 80,
            "Tier 3": 60,
            "Tier 4": 40,
            "Specialty": 50,
            "Excluded": 0
        }
        
        # Calculate lives-weighted access score
        total_lives = sum(tier_distribution.values())
        weighted_access_score = 0.0
        
        for tier, lives in tier_distribution.items():
            base_score = tier_scores.get(tier, 50)
            access_score = access_scores.get(tier, base_score)
            weighted_access_score += (access_score * lives / total_lives) if total_lives > 0 else 0
        
        # Map access score to rebate % (simplified function)
        # Higher access score = lower rebate
        rebate_percent = max(0, min(50, (100 - weighted_access_score) * 0.5))
        
        # Calculate net price
        fees = wac * 0.02  # 2% fees
        chargebacks = wac * 0.01  # 1% chargebacks
        net_price = wac * (1 - rebate_percent / 100) - fees - chargebacks
        
        return {
            "asset_id": asset_id,
            "channel": channel,
            "wac": wac,
            "tier_distribution": tier_distribution,
            "access_score": weighted_access_score,
            "rebate_percent": rebate_percent,
            "fees": fees,
            "chargebacks": chargebacks,
            "net_price": net_price,
            "calculated_at": datetime.now().isoformat()
        }
    
    def calculate_npv(
        self,
        asset_id: str,
        cash_flows: List[Dict[str, Any]],
        discount_rate: float = 0.10,
        probability_of_success: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate NPV and rNPV
        
        CashFlow_t = NetSales_t − COGS_t − OPEX_t − LaunchCosts_t
        NPV = Σ CashFlow_t / (1 + r)^t
        rNPV = Σ (CashFlow_t × PoS_stage(t)) / (1 + r)^t
        """
        npv = 0.0
        rnpv = 0.0
        
        for t, cf in enumerate(cash_flows):
            cash_flow = cf.get("cash_flow", 0)
            year = cf.get("year", datetime.now().year + t)
            
            # Discount factor
            discount_factor = 1 / ((1 + discount_rate) ** t)
            
            # NPV
            npv += cash_flow * discount_factor
            
            # rNPV (if PoS provided)
            if probability_of_success:
                pos = probability_of_success
                rnpv += cash_flow * pos * discount_factor
        
        result = {
            "asset_id": asset_id,
            "npv": float(npv),
            "rnpv": float(rnpv) if probability_of_success else None,
            "discount_rate": discount_rate,
            "probability_of_success": probability_of_success,
            "calculated_at": datetime.now().isoformat()
        }
        
        # Store
        key = f"{asset_id}_npv"
        self._financial_projections[key] = result
        
        return result
    
    def calculate_roi(
        self,
        asset_id: str,
        total_investment: float,
        total_benefits: float,
        discount_rate: float = 0.10,
        years: int = 10,
        start_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculate ROI with curve generation
        
        ROI = (ΣDiscountedBenefits − ΣDiscountedCosts) / ΣDiscountedCosts
        """
        if start_year is None:
            start_year = datetime.now().year
        
        discounted_benefits = total_benefits / (1 + discount_rate)
        discounted_costs = total_investment / (1 + discount_rate)
        
        roi = ((discounted_benefits - discounted_costs) / discounted_costs) if discounted_costs > 0 else 0
        
        # Generate ROI curve over time
        roi_curve = []
        cumulative_investment = 0.0
        cumulative_benefits = 0.0
        
        # Assume investment is front-loaded (years 0-3) and benefits accrue over time
        investment_per_year = total_investment / 3 if years >= 3 else total_investment / years
        benefits_per_year = total_benefits / years
        
        for year_offset in range(years):
            year = start_year + year_offset
            if year_offset < 3:
                cumulative_investment += investment_per_year / ((1 + discount_rate) ** year_offset)
            cumulative_benefits += benefits_per_year / ((1 + discount_rate) ** year_offset)
            
            year_roi = ((cumulative_benefits - cumulative_investment) / cumulative_investment) if cumulative_investment > 0 else 0
            
            roi_curve.append({
                "year": year,
                "year_offset": year_offset,
                "cumulative_investment": float(cumulative_investment),
                "cumulative_benefits": float(cumulative_benefits),
                "roi": float(year_roi),
                "net_value": float(cumulative_benefits - cumulative_investment)
            })
        
        result = {
            "asset_id": asset_id,
            "roi": float(roi),
            "total_investment": total_investment,
            "total_benefits": total_benefits,
            "discount_rate": discount_rate,
            "roi_curve": roi_curve,
            "start_year": start_year,
            "calculated_at": datetime.now().isoformat()
        }
        
        # Store ROI curve
        key = f"{asset_id}_roi"
        self._roi_curves[key] = result
        
        return result
    
    def calculate_roi_curves_multiple_scenarios(
        self,
        asset_id: str,
        base_investment: float,
        base_benefits: float,
        discount_rate: float = 0.10,
        years: int = 10,
        start_year: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Calculate ROI curves for multiple scenarios (base, optimistic, pessimistic)
        All scenarios use the same year range for proper chart alignment
        """
        if start_year is None:
            start_year = datetime.now().year
        
        scenarios = {
            "base": {"investment_mult": 1.0, "benefits_mult": 1.0},
            "optimistic": {"investment_mult": 0.9, "benefits_mult": 1.3},
            "pessimistic": {"investment_mult": 1.2, "benefits_mult": 0.7}
        }
        
        scenario_results = {}
        for scenario_name, multipliers in scenarios.items():
            investment = base_investment * multipliers["investment_mult"]
            benefits = base_benefits * multipliers["benefits_mult"]
            
            roi_result = self.calculate_roi(
                asset_id=f"{asset_id}_{scenario_name}",
                total_investment=investment,
                total_benefits=benefits,
                discount_rate=discount_rate,
                years=years,
                start_year=start_year
            )
            
            # Ensure all scenarios use the same year range
            # Rebuild roi_curve with consistent years
            if roi_result.get("roi_curve"):
                aligned_curve = []
                for year_offset in range(years):
                    year = start_year + year_offset
                    # Find matching entry or interpolate
                    matching_entry = next(
                        (entry for entry in roi_result["roi_curve"] if entry.get("year") == year),
                        None
                    )
                    if matching_entry:
                        aligned_curve.append({
                            "year": year,
                            "roi": matching_entry.get("roi", 0),
                            "cumulative_investment": matching_entry.get("cumulative_investment", 0),
                            "cumulative_benefits": matching_entry.get("cumulative_benefits", 0),
                            "net_value": matching_entry.get("net_value", 0)
                        })
                    else:
                        # Use the closest entry or calculate
                        closest = min(
                            roi_result["roi_curve"],
                            key=lambda x: abs(x.get("year", start_year) - year)
                        )
                        aligned_curve.append({
                            "year": year,
                            "roi": closest.get("roi", 0),
                            "cumulative_investment": closest.get("cumulative_investment", 0),
                            "cumulative_benefits": closest.get("cumulative_benefits", 0),
                            "net_value": closest.get("net_value", 0)
                        })
                roi_result["roi_curve"] = aligned_curve
            
            scenario_results[scenario_name] = roi_result
        
        return {
            "asset_id": asset_id,
            "scenarios": scenario_results,
            "start_year": start_year,
            "years": years,
            "calculated_at": datetime.now().isoformat()
        }
    
    def _calculate_prevalence_from_claims(
        self,
        data_loader: OptimizedDataLoader,
        indication: str
    ) -> Optional[Dict[str, Any]]:
        """Calculate prevalence from claims data for an indication"""
        try:
            claims_df = data_loader.get_data('claims')
            if claims_df is None or claims_df.empty:
                return None
            
            # Direct calculation from claims data (synchronous)
            # Search for indication-related ICD codes
            diagnosis_cols = [col for col in claims_df.columns if col.startswith('D') and col != 'DIAGNOSIS_CODE']
            if not diagnosis_cols:
                diagnosis_cols = ['DIAGNOSIS_CODE'] if 'DIAGNOSIS_CODE' in claims_df.columns else []
            
            if not diagnosis_cols:
                return None
            
            # Search for indication in diagnosis columns
            mask = pd.Series([False] * len(claims_df))
            indication_lower = indication.lower()
            
            # Track which columns had matches
            columns_searched = []
            columns_with_matches = []
            
            for col in diagnosis_cols:
                try:
                    col_mask = claims_df[col].astype(str).str.contains(indication_lower, case=False, na=False)
                    columns_searched.append(col)
                    if col_mask.any():
                        columns_with_matches.append(col)
                    mask |= col_mask
                except Exception:
                    continue
            
            matching_claims = claims_df[mask]
            
            if matching_claims.empty:
                return None
            
            # Extract unique ICD codes that matched
            matched_icd_codes = set()
            for col in columns_with_matches:
                try:
                    codes = matching_claims[col].dropna().astype(str).unique()
                    matched_icd_codes.update([c for c in codes if indication_lower in c.lower()])
                except Exception:
                    continue
            
            # Count unique patients
            patient_col = 'PATIENT_ID' if 'PATIENT_ID' in matching_claims.columns else 'Patient_ID'
            if patient_col not in matching_claims.columns:
                # Try PATIENT_TOKEN_1 (from actual claims data structure)
                patient_col = 'PATIENT_TOKEN_1' if 'PATIENT_TOKEN_1' in matching_claims.columns else None
                if patient_col:
                    total_patients = matching_claims[patient_col].nunique()
                else:
                    total_patients = len(matching_claims)
            else:
                total_patients = matching_claims[patient_col].nunique()
            
            # Count total claims
            total_claims = len(matching_claims)
            
            # Extrapolate to full US population (15% sample rate)
            claims_sample_rate = 0.15
            estimated_us_population = total_patients / claims_sample_rate
            
            # Calculate prevalence rate
            us_total_population = 330000000  # US population
            prevalence_rate = estimated_us_population / us_total_population
            
            return {
                "prevalence": float(prevalence_rate),
                "total_patients": int(estimated_us_population),
                "indication": indication,
                "source": "claims_data",
                "calculation_details": {
                    "data_source": "Claims Database (combined_claims.csv)",
                    "search_method": "Text-based search for indication in diagnosis columns",
                    "indication_searched": indication,
                    "diagnosis_columns_searched": columns_searched,
                    "diagnosis_columns_with_matches": columns_with_matches,
                    "patient_identifier_column": patient_col or "row_count",
                    "claims_sample_rate": claims_sample_rate,
                    "us_total_population": us_total_population,
                    "calculation_steps": [
                        f"1. Searched for '{indication}' in diagnosis columns: {', '.join(columns_searched)}",
                        f"2. Found {total_claims:,} matching claims",
                        f"3. Identified {total_patients:,} unique patients in sample",
                        f"4. Extrapolated to US population: {total_patients:,} / {claims_sample_rate} = {int(estimated_us_population):,} patients",
                        f"5. Calculated prevalence: {int(estimated_us_population):,} / {us_total_population:,} = {(prevalence_rate * 100):.4f}%"
                    ],
                    "matched_icd_codes": sorted(list(matched_icd_codes))[:50],  # Limit to first 50 for display
                    "total_matched_icd_codes": len(matched_icd_codes),
                    "sample_statistics": {
                        "total_claims_in_sample": total_claims,
                        "unique_patients_in_sample": total_patients,
                        "estimated_us_patients": int(estimated_us_population)
                    }
                }
            }
        except Exception as e:
            # If calculation fails, return None
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error calculating prevalence from claims: {e}")
            return None
    
    def get_patient_funnel(self, asset_id: str, market: str) -> Optional[Dict[str, Any]]:
        """Get stored patient funnel"""
        key = f"{asset_id}_{market}"
        return self._patient_funnels.get(key)
    
    def get_revenue_projection(self, asset_id: str, market: str) -> Optional[Dict[str, Any]]:
        """Get stored revenue projection"""
        key = f"{asset_id}_{market}"
        return self._revenue_projections.get(key)


# Global instance
financial_modeling_service = FinancialModelingService()


