"""
US GTN Service - US-specific formulary tiering and access-based rebates
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


class USGTNService:
    """Service for US GTN calculations with formulary tiering"""
    
    def __init__(self):
        # In-memory storage
        self._us_gtn_calculations: Dict[str, Dict[str, Any]] = {}
        self._access_scores: Dict[str, Dict[str, float]] = {}
    
    def calculate_access_score(
        self,
        tier: str,
        has_pa: bool = False,
        has_step_therapy: bool = False,
        has_quantity_limits: bool = False,
        is_preferred: bool = False,
        is_excluded: bool = False
    ) -> float:
        """
        Calculate access score for a plan
        
        AccessScore_plan = BaseTierScore(tier) − UM_Penalty(PA/ST/QL) + PreferredBonus − ExclusionPenalty
        """
        # Base tier scores
        tier_scores = {
            "Tier 2": 80,
            "Tier 3": 60,
            "Tier 4": 40,
            "Specialty": 50,
            "Excluded": 0
        }
        
        base_score = tier_scores.get(tier, 50)
        
        # UM penalties
        um_penalty = 0
        if has_pa:
            um_penalty += 10
        if has_step_therapy:
            um_penalty += 15
        if has_quantity_limits:
            um_penalty += 5
        
        # Preferred bonus
        preferred_bonus = 5 if is_preferred else 0
        
        # Exclusion penalty
        exclusion_penalty = 100 if is_excluded else 0
        
        # Calculate final score
        access_score = base_score - um_penalty + preferred_bonus - exclusion_penalty
        
        return max(0, min(100, access_score))
    
    def map_access_score_to_rebate(
        self,
        access_score: float,
        channel: str = "commercial",
        competitor_position: str = "moderate",
        price_aggressiveness: float = 0.5
    ) -> float:
        """
        Map access score to expected rebate percentage
        
        ExpectedRebate%_plan = f_channel(AccessScore_plan, CompetitorPosition, PriceAggressiveness)
        """
        # Base rebate from access score (inverse relationship)
        base_rebate = (100 - access_score) * 0.5  # 0-50% range
        
        # Adjust for competitor position
        competitor_adjustment = 0
        if competitor_position == "strong":
            competitor_adjustment = -5  # Lower rebate needed
        elif competitor_position == "weak":
            competitor_adjustment = 5  # Higher rebate needed
        
        # Adjust for price aggressiveness
        price_adjustment = (price_aggressiveness - 0.5) * 10  # -5% to +5%
        
        final_rebate = base_rebate + competitor_adjustment + price_adjustment
        
        return max(0, min(50, final_rebate))
    
    def calculate_channel_net_price(
        self,
        asset_id: str,
        channel: str,
        wac: float,
        tier_distribution: Dict[str, float],  # {tier: lives}
        access_scores: Dict[str, float],  # {tier: access_score}
        fees: float = 0.0,
        chargebacks: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculate channel net price
        
        Rebate%_channel = (Σplans Lives_plan × ExpectedRebate%_plan) / (Σplans Lives_plan)
        NetPrice_channel = WAC × (1 − Rebate%_channel) − Fees − Chargebacks
        """
        # Calculate lives-weighted rebate
        total_lives = sum(tier_distribution.values())
        weighted_rebate = 0.0
        
        for tier, lives in tier_distribution.items():
            access_score = access_scores.get(tier, 50)
            rebate_pct = self.map_access_score_to_rebate(access_score, channel=channel)
            weighted_rebate += (rebate_pct * lives / total_lives) if total_lives > 0 else 0
        
        # Calculate net price
        net_price = wac * (1 - weighted_rebate / 100) - fees - chargebacks
        
        return {
            "asset_id": asset_id,
            "channel": channel,
            "wac": wac,
            "tier_distribution": tier_distribution,
            "lives_weighted_rebate": weighted_rebate,
            "fees": fees,
            "chargebacks": chargebacks,
            "net_price": net_price,
            "calculated_at": datetime.now().isoformat()
        }
    
    def calculate_us_blended_net(
        self,
        asset_id: str,
        channel_prices: List[Dict[str, Any]],
        channel_units: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Calculate US blended net price
        
        NetPrice_US = Σchannel (NetPrice_channel × Units_channel) / Σchannel Units_channel
        """
        total_units = sum(channel_units.values())
        weighted_net = 0.0
        
        for channel_price in channel_prices:
            channel = channel_price["channel"]
            net_price = channel_price["net_price"]
            units = channel_units.get(channel, 0)
            weighted_net += (net_price * units / total_units) if total_units > 0 else 0
        
        return {
            "asset_id": asset_id,
            "blended_net_price": weighted_net,
            "channel_breakdown": channel_prices,
            "calculated_at": datetime.now().isoformat()
        }


# Global instance
us_gtn_service = USGTNService()


