"""
AI Scenario Generator - Natural language scenario generation and parsing
Generates scenarios considering timeline, pricing, coverage, competitors, and market dynamics
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import re
from agents.llm_agent import llm_agent
from services.price_potential_engine import price_potential_engine
from services.hta_intelligence_service import hta_intelligence_service
from services.financial_modeling_service import financial_modeling_service
from services.payer_data_service import payer_data_service
from utils.optimized_data_loader import OptimizedDataLoader
import logging

logger = logging.getLogger(__name__)


class AIScenarioGenerator:
    """Generate and parse AI-powered scenarios from natural language"""
    
    def __init__(self, data_loader: Optional[OptimizedDataLoader] = None):
        self.data_loader = data_loader or OptimizedDataLoader()
    
    async def generate_scenario_from_text(
        self,
        asset_id: str,
        scenario_description: str,
        asset_context: Optional[Dict[str, Any]] = None,
        market: str = "US"
    ) -> Dict[str, Any]:
        """
        Generate a structured scenario from natural language description
        
        Examples:
        - "6 months faster submission with priority review voucher"
        - "Increase list price by $50K but don't get coverage"
        - "Competitor launches 3 months earlier, reduce market share by 20%"
        - "Use priority review voucher, get restricted coverage, increase price by 25%"
        """
        try:
            # Gather context from other tabs/services
            context = await self._gather_asset_context(asset_id, asset_context, market)
            
            # Parse scenario description using LLM
            parsed_scenario = await self._parse_scenario_description(
                scenario_description, context, asset_id, market
            )
            
            # Enhance with data-driven insights
            enhanced_scenario = await self._enhance_scenario_with_data(
                parsed_scenario, asset_id, market, context
            )
            
            return enhanced_scenario
            
        except Exception as e:
            logger.error(f"Error generating scenario from text: {e}", exc_info=True)
            raise
    
    async def _gather_asset_context(
        self,
        asset_id: str,
        asset_context: Optional[Dict[str, Any]],
        market: str
    ) -> Dict[str, Any]:
        """Gather context from pricing, coverage, competitors, HTA, and financial data"""
        context = {
            "asset_id": asset_id,
            "market": market,
            "timestamp": datetime.now().isoformat()
        }
        
        # Get asset data if provided
        if asset_context:
            context.update({
                "current_list_price": asset_context.get("list_price"),
                "indication": asset_context.get("indication"),
                "therapeutic_area": asset_context.get("therapeutic_area"),
                "development_stage": asset_context.get("development_stage"),
                "current_launch_date": asset_context.get("launch_date"),
                "comparators": asset_context.get("comparators", []),
            })
        
        # Get current pricing/coverage data
        try:
            if asset_context and asset_context.get("list_price"):
                list_price = asset_context.get("list_price")
                waterfall = price_potential_engine.calculate_waterfall(
                    asset_id=asset_id,
                    market=market,
                    list_price=list_price
                )
                context["current_net_price"] = waterfall.get("net_price")
                context["current_gtn_breakdown"] = waterfall.get("gtn_breakdown", {})
        except Exception as e:
            logger.warning(f"Could not get pricing context: {e}")
        
        # Get HTA context
        try:
            if asset_context:
                hta_pathway = hta_intelligence_service.get_hta_pathway(asset_id, market)
                context["hta_pathway"] = hta_pathway
                context["typical_hta_timeline_months"] = hta_pathway.get("total_timeline_months", 12)
        except Exception as e:
            logger.warning(f"Could not get HTA context: {e}")
        
        # Get competitor context
        try:
            if asset_context and asset_context.get("comparators"):
                comparators = asset_context.get("comparators", [])
                context["competitor_count"] = len(comparators)
                # Extract competitor timelines if available
                competitor_timelines = []
                for comp in comparators:
                    if comp.get("launch_date"):
                        competitor_timelines.append({
                            "name": comp.get("name", "Unknown"),
                            "launch_date": comp.get("launch_date")
                        })
                context["competitor_timelines"] = competitor_timelines
        except Exception as e:
            logger.warning(f"Could not get competitor context: {e}")
        
        # Get coverage context
        try:
            if asset_context and asset_context.get("indication"):
                indication = asset_context.get("indication")
                drug_name = asset_context.get("drug_name") or asset_context.get("name")
                if drug_name:
                    coverage = payer_data_service.get_formulary_coverage(drug_name, indication)
                    if coverage:
                        context["current_coverage"] = coverage.get("coverage_level")
                        context["current_tier"] = coverage.get("tier")
        except Exception as e:
            logger.warning(f"Could not get coverage context: {e}")
        
        return context
    
    async def _parse_scenario_description(
        self,
        scenario_description: str,
        context: Dict[str, Any],
        asset_id: str,
        market: str
    ) -> Dict[str, Any]:
        """Use LLM to parse natural language scenario into structured parameters"""
        
        system_prompt = """You are an expert pharmaceutical strategy analyst. Parse natural language scenario descriptions into structured parameters.

Extract the following types of changes:
1. TIMELINE CHANGES:
   - Faster submission (e.g., "6 months faster", "accelerate by 3 months")
   - Priority review voucher (e.g., "use priority review voucher", "PRV")
   - Regulatory delays (e.g., "3 month delay", "FDA requests additional data")
   - Launch date changes (e.g., "launch 1 year earlier", "delay launch by 6 months")

2. PRICING CHANGES:
   - List price adjustments (e.g., "increase by $50K", "reduce by 20%", "set to $100K")
   - Net price changes (e.g., "increase net price by 15%")
   - Rebate changes (e.g., "reduce rebates by 5%")

3. COVERAGE CHANGES:
   - Coverage denial (e.g., "don't get coverage", "no formulary coverage")
   - Restricted coverage (e.g., "restricted coverage", "prior authorization required")
   - Tier changes (e.g., "move to tier 3", "excluded from formulary")

4. COMPETITOR CHANGES:
   - Competitor timeline changes (e.g., "competitor launches 3 months earlier")
   - Market share impact (e.g., "reduce market share by 20%", "lose 15% share to competitor")
   - Competitive pricing (e.g., "competitor reduces price by 10%")

5. MARKET DYNAMICS:
   - Market size changes (e.g., "market grows by 25%", "smaller addressable market")
   - Uptake changes (e.g., "slower uptake", "faster adoption")

Return ONLY valid JSON in this exact format:
{
  "scenario_name": "Brief descriptive name",
  "timeline_changes": {
    "submission_acceleration_months": 0,  // Positive = faster, negative = slower
    "use_priority_review_voucher": false,
    "regulatory_delay_months": 0,
    "launch_date_shift_months": 0  // Positive = earlier, negative = later
  },
  "pricing_changes": {
    "list_price_adjustment_dollars": 0,  // Absolute change in dollars
    "list_price_adjustment_percent": 0,  // Percentage change
    "net_price_adjustment_percent": 0,
    "rebate_adjustment_percent": 0
  },
  "coverage_changes": {
    "coverage_level": null,  // "Unrestricted", "Restricted", "Not Covered", "Not Listed/Unknown", or null if unchanged
    "tier": null,  // "Tier 1", "Tier 2", etc., or null if unchanged
    "restrictions": []  // ["PA", "ST", "QL"] or []
  },
  "competitor_changes": {
    "competitor_launch_shift_months": 0,  // Positive = competitor launches earlier, negative = later
    "market_share_impact_percent": 0,  // Negative = lose share, positive = gain share
    "competitor_price_change_percent": 0
  },
  "market_dynamics": {
    "market_size_change_percent": 0,
    "uptake_rate_adjustment": 0  // Multiplier (1.0 = no change, 0.8 = 20% slower, 1.2 = 20% faster)
  },
  "rationale": "Explanation of how the scenario description was interpreted",
  "assumptions": ["List of key assumptions made"]
}"""

        user_prompt = f"""Parse this scenario description into structured parameters:

Scenario: "{scenario_description}"

Current Asset Context:
- Asset ID: {asset_id}
- Market: {market}
- Current List Price: ${context.get('current_list_price', 'Unknown'):,.0f} (if available)
- Current Net Price: ${context.get('current_net_price', 'Unknown'):,.0f} (if available)
- Current Coverage: {context.get('current_coverage', 'Unknown')}
- Development Stage: {context.get('development_stage', 'Unknown')}
- Typical HTA Timeline: {context.get('typical_hta_timeline_months', 12)} months
- Competitors: {context.get('competitor_count', 0)} identified

Extract all changes mentioned in the scenario description. If a parameter is not mentioned, set it to 0 or null (unchanged)."""

        try:
            response_text = await llm_agent.generate_structured_response(
                user_prompt, system_prompt
            )
            
            # Parse JSON response
            parsed = json.loads(response_text)
            
            # Validate and set defaults
            parsed.setdefault("scenario_name", scenario_description[:100])
            parsed.setdefault("timeline_changes", {})
            parsed.setdefault("pricing_changes", {})
            parsed.setdefault("coverage_changes", {})
            parsed.setdefault("competitor_changes", {})
            parsed.setdefault("market_dynamics", {})
            parsed.setdefault("rationale", "")
            parsed.setdefault("assumptions", [])
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response text: {response_text}")
            # Return minimal scenario
            return {
                "scenario_name": scenario_description[:100],
                "timeline_changes": {},
                "pricing_changes": {},
                "coverage_changes": {},
                "competitor_changes": {},
                "market_dynamics": {},
                "rationale": "Failed to parse scenario - using defaults",
                "assumptions": ["Scenario parsing failed, using minimal parameters"]
            }
    
    async def _enhance_scenario_with_data(
        self,
        parsed_scenario: Dict[str, Any],
        asset_id: str,
        market: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance parsed scenario with data-driven insights and calculations"""
        
        enhanced = {
            **parsed_scenario,
            "asset_id": asset_id,
            "market": market,
            "generated_at": datetime.now().isoformat(),
            "data_enhancements": {}
        }
        
        # Calculate new launch date based on timeline changes
        timeline_changes = parsed_scenario.get("timeline_changes", {})
        if timeline_changes:
            current_launch = context.get("current_launch_date")
            if current_launch:
                try:
                    if isinstance(current_launch, str):
                        current_date = datetime.fromisoformat(current_launch.replace('Z', '+00:00'))
                    else:
                        current_date = current_launch
                    
                    # Calculate total shift
                    submission_accel = timeline_changes.get("submission_acceleration_months", 0)
                    regulatory_delay = timeline_changes.get("regulatory_delay_months", 0)
                    launch_shift = timeline_changes.get("launch_date_shift_months", 0)
                    
                    # Priority review voucher typically saves 4 months
                    prv_months = -4 if timeline_changes.get("use_priority_review_voucher", False) else 0
                    
                    total_shift_months = submission_accel - regulatory_delay + launch_shift + prv_months
                    new_launch_date = current_date + timedelta(days=total_shift_months * 30)
                    
                    enhanced["calculated_launch_date"] = new_launch_date.isoformat()
                    enhanced["launch_date_shift_months"] = total_shift_months
                except Exception as e:
                    logger.warning(f"Could not calculate launch date: {e}")
        
        # Calculate new list price
        pricing_changes = parsed_scenario.get("pricing_changes", {})
        current_list_price = context.get("current_list_price")
        if current_list_price and pricing_changes:
            new_list_price = current_list_price
            
            # Apply dollar adjustment
            dollar_adj = pricing_changes.get("list_price_adjustment_dollars", 0)
            new_list_price += dollar_adj
            
            # Apply percentage adjustment
            pct_adj = pricing_changes.get("list_price_adjustment_percent", 0)
            new_list_price *= (1 + pct_adj / 100)
            
            enhanced["calculated_list_price"] = new_list_price
            enhanced["list_price_change"] = new_list_price - current_list_price
        
        # Calculate market share impact
        competitor_changes = parsed_scenario.get("competitor_changes", {})
        market_share_impact = competitor_changes.get("market_share_impact_percent", 0)
        if market_share_impact:
            enhanced["data_enhancements"]["market_share_impact"] = {
                "impact_percent": market_share_impact,
                "note": f"Market share will {'increase' if market_share_impact > 0 else 'decrease'} by {abs(market_share_impact)}%"
            }
        
        # Add coverage impact analysis
        coverage_changes = parsed_scenario.get("coverage_changes", {})
        if coverage_changes.get("coverage_level"):
            new_coverage = coverage_changes.get("coverage_level")
            current_coverage = context.get("current_coverage", "Unknown")
            enhanced["data_enhancements"]["coverage_impact"] = {
                "current_coverage": current_coverage,
                "new_coverage": new_coverage,
                "impact": "Significant" if new_coverage == "Not Covered" else "Moderate"
            }
        
        return enhanced
    
    def convert_to_scenario_params(
        self,
        enhanced_scenario: Dict[str, Any],
        base_scenario: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Convert enhanced scenario to scenario engine parameters
        
        This bridges the AI-generated scenario to the scenario engine format
        """
        base = base_scenario or {}
        
        # Start with base scenario
        params = {**base}
        
        # Apply timeline changes
        timeline = enhanced_scenario.get("timeline_changes", {})
        if enhanced_scenario.get("calculated_launch_date"):
            params["launch_date"] = enhanced_scenario["calculated_launch_date"]
        
        # Apply pricing changes
        pricing = enhanced_scenario.get("pricing_changes", {})
        if enhanced_scenario.get("calculated_list_price"):
            params["list_price"] = enhanced_scenario["calculated_list_price"]
        
        # Apply coverage changes (affects HTA outcome)
        coverage = enhanced_scenario.get("coverage_changes", {})
        coverage_level = coverage.get("coverage_level")
        if coverage_level:
            # Map coverage level to HTA outcome
            if coverage_level == "Not Covered":
                params["hta_outcome"] = "rejection"
            elif coverage_level == "Restricted":
                params["hta_outcome"] = "restriction"
            else:
                params["hta_outcome"] = "approval"
        
        # Apply market dynamics
        market_dynamics = enhanced_scenario.get("market_dynamics", {})
        uptake_adjustment = market_dynamics.get("uptake_rate_adjustment", 1.0)
        if uptake_adjustment != 1.0:
            # Adjust uptake archetype or add custom parameter
            current_uptake = params.get("uptake_archetype", "moderate")
            if uptake_adjustment < 0.8:
                params["uptake_archetype"] = "slow"
            elif uptake_adjustment > 1.2:
                params["uptake_archetype"] = "fast"
            params["uptake_multiplier"] = uptake_adjustment
        
        # Apply competitor market share impact
        competitor = enhanced_scenario.get("competitor_changes", {})
        market_share_impact = competitor.get("market_share_impact_percent", 0)
        if market_share_impact:
            # Adjust market share in units calculation
            current_units = params.get("units", 1000)
            params["units"] = current_units * (1 + market_share_impact / 100)
        
        # Add scenario metadata
        params["scenario_name"] = enhanced_scenario.get("scenario_name", "AI Generated Scenario")
        params["scenario_description"] = enhanced_scenario.get("rationale", "")
        params["ai_generated"] = True
        params["generated_at"] = enhanced_scenario.get("generated_at")
        
        return params


# Global instance
ai_scenario_generator = AIScenarioGenerator()
