"""
Rules Engine
Applies business rules (Golden, Country, Indication) to CPP calculations
"""

import logging
from typing import List, Dict, Optional
from decimal import Decimal

from models.cpp_models import Rule, RuleApplication, RuleAction
from services.cpp_data_loaders import get_cpp_data_loader

logger = logging.getLogger(__name__)


class RulesEngine:
    """
    Engine for applying business rules to budget calculations
    
    Rules types:
    - Golden Rules: Apply to all studies
    - Country Rules: Apply based on country
    - Indication Rules: Apply based on therapeutic area/indication
    """
    
    def __init__(self):
        self.data_loader = get_cpp_data_loader()
    
    def apply_rules(
        self,
        base_amount: Decimal,
        context: Dict[str, any]
    ) -> Dict[str, any]:
        """
        Apply all applicable rules to a base amount
        
        Args:
            base_amount: Starting amount (e.g., direct procedure costs)
            context: Dict with study context (country, indication, phase, etc.)
            
        Returns:
            Dict with adjusted_amount, applications, and breakdown
        """
        # Get applicable rules
        applicable_rules = self.data_loader.get_rules_for_context(context)
        
        if not applicable_rules:
            logger.info("No applicable rules found")
            return {
                'original_amount': float(base_amount),
                'adjusted_amount': float(base_amount),
                'rule_applications': [],
                'total_adjustment': 0.0
            }
        
        # Apply rules in order
        current_amount = base_amount
        applications = []
        
        for rule in applicable_rules:
            adjusted_amount, application = self._apply_single_rule(
                current_amount,
                rule,
                context
            )
            
            if application:
                applications.append(application)
                current_amount = adjusted_amount
        
        total_adjustment = float(current_amount - base_amount)
        
        return {
            'original_amount': float(base_amount),
            'adjusted_amount': float(current_amount),
            'rule_applications': applications,
            'total_adjustment': total_adjustment,
            'num_rules_applied': len(applications)
        }
    
    def _apply_single_rule(
        self,
        amount: Decimal,
        rule: Rule,
        context: Dict[str, any]
    ) -> tuple[Decimal, Optional[RuleApplication]]:
        """
        Apply a single rule to an amount
        
        Returns (new_amount, RuleApplication or None)
        """
        if not rule.active:
            return amount, None
        
        action = rule.action
        value = Decimal(str(rule.value))
        
        try:
            if action == RuleAction.ADD_COST:
                # Add fixed cost
                new_amount = amount + value
                applied_value = float(value)
            
            elif action == RuleAction.MULTIPLY:
                # Multiply by factor
                new_amount = amount * value
                applied_value = float(new_amount - amount)
            
            elif action == RuleAction.ADD_PERCENTAGE:
                # Add percentage of amount
                adjustment = amount * (value / Decimal('100'))
                new_amount = amount + adjustment
                applied_value = float(adjustment)
            
            elif action == RuleAction.SET_VALUE:
                # Set to specific value
                new_amount = value
                applied_value = float(new_amount - amount)
            
            else:
                logger.warning(f"Unknown rule action: {action}")
                return amount, None
            
            application = RuleApplication(
                rule_id=rule.id,
                rule_name=rule.name,
                applied_value=applied_value,
                context={
                    'action': action.value,
                    'rule_type': rule.rule_type.value,
                    'description': rule.description
                }
            )
            
            logger.debug(
                f"Applied rule '{rule.name}': {float(amount)} -> {float(new_amount)} "
                f"(adjustment: {applied_value})"
            )
            
            return new_amount, application
        
        except Exception as e:
            logger.error(f"Error applying rule '{rule.name}': {e}")
            return amount, None
    
    def get_applicable_rules_preview(self, context: Dict[str, any]) -> List[Dict[str, any]]:
        """
        Get preview of rules that would apply to a context
        
        Useful for showing users what rules will be applied
        """
        rules = self.data_loader.get_rules_for_context(context)
        
        preview = []
        for rule in rules:
            preview.append({
                'id': rule.id,
                'name': rule.name,
                'type': rule.rule_type.value,
                'description': rule.description,
                'action': rule.action.value,
                'value': rule.value,
                'priority': rule.priority
            })
        
        return preview
    
    def calculate_compound_adjustments(
        self,
        base_amount: Decimal,
        adjustments: List[Dict[str, any]]
    ) -> Decimal:
        """
        Calculate compound effect of multiple adjustments
        
        Useful for "what-if" scenarios
        
        Args:
            base_amount: Starting amount
            adjustments: List of {action: str, value: float}
            
        Returns:
            Final adjusted amount
        """
        current = base_amount
        
        for adj in adjustments:
            action_str = adj.get('action', 'add_percentage')
            value = Decimal(str(adj.get('value', 0)))
            
            if action_str == 'add_cost':
                current += value
            elif action_str == 'multiply':
                current *= value
            elif action_str == 'add_percentage':
                current += current * (value / Decimal('100'))
            elif action_str == 'set_value':
                current = value
        
        return current


# Global singleton
_rules_engine = None

def get_rules_engine() -> RulesEngine:
    """Get or create global rules engine instance"""
    global _rules_engine
    if _rules_engine is None:
        _rules_engine = RulesEngine()
    return _rules_engine







