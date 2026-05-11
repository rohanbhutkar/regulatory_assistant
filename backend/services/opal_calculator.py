"""
OPAL Calculator Service
Calculates overhead staffing hours based on study complexity
"""

import logging
from typing import Dict, List, Optional
from decimal import Decimal

from models.cpp_models import OPALInput, OPALResult, StudyType, Phase

logger = logging.getLogger(__name__)


class OPALCalculator:
    """
    Calculator for OPAL (Overhead Per-Patient Labor) hours
    
    Implements OPAL calculation logic:
    1. Calculate raw OPAL score (1-8) based on study characteristics
    2. Apply modifiers (+0 to +4.5) for special requirements
    3. Calculate adjusted OPAL score
    4. Distribute hours across staff roles by visit type
    """
    
    # Distribution of Labor percentages by visit type and role
    # Based on OPAL reference tables
    STAFF_DISTRIBUTION = {
        "Screening/Baseline": {
            "PI": 0.15,
            "Nurse": 0.40,
            "CRC": 0.35,
            "CRA": 0.10
        },
        "Treatment Visit": {
            "PI": 0.10,
            "Nurse": 0.45,
            "CRC": 0.30,
            "CRA": 0.15
        },
        "Follow-Up Visit": {
            "PI": 0.08,
            "Nurse": 0.35,
            "CRC": 0.40,
            "CRA": 0.17
        },
        "Unscheduled Visit": {
            "PI": 0.12,
            "Nurse": 0.50,
            "CRC": 0.28,
            "CRA": 0.10
        },
        "Pre-Screening": {
            "PI": 0.05,
            "Nurse": 0.20,
            "CRC": 0.60,
            "CRA": 0.15
        }
    }
    
    def __init__(self):
        pass
    
    def calculate(self, opal_input: OPALInput) -> OPALResult:
        """
        Calculate OPAL overhead hours
        
        Args:
            opal_input: OPALInput with study characteristics
            
        Returns:
            OPALResult with calculated hours and distributions
        """
        # Step 1: Calculate raw OPAL score
        raw_score = self._calculate_raw_score(opal_input)
        
        # Step 2: Calculate modifier adjustments
        modifier_score = self._calculate_modifiers(opal_input)
        
        # Step 3: Calculate adjusted score
        adjusted_score = raw_score + modifier_score
        
        # Step 4: Calculate total overhead hours
        # Base: adjusted_score represents hours per visit
        total_overhead_hours = adjusted_score
        
        # Step 5: Distribute hours across staff roles
        staff_distribution = self._distribute_hours(adjusted_score)
        
        # Build calculation details
        calculation_details = {
            "raw_score_breakdown": self._get_raw_score_reasoning(opal_input),
            "modifier_breakdown": self._get_modifier_reasoning(opal_input),
            "total_hours": total_overhead_hours
        }
        
        return OPALResult(
            raw_score=raw_score,
            modifier_score=modifier_score,
            adjusted_score=adjusted_score,
            total_overhead_hours=total_overhead_hours,
            staff_distribution=staff_distribution,
            calculation_details=calculation_details
        )
    
    def _calculate_raw_score(self, opal_input: OPALInput) -> float:
        """
        Calculate raw OPAL score (1-8) based on study characteristics
        
        Decision tree:
        - Early Termination studies = 8
        - Phase I with 1-2 visits = 1-2
        - Observational OR Interventional with no procedures = 3
        - One procedure type = 4-5
        - Multiple procedure types = 6-7
        """
        study_type = opal_input.study_type
        phase = opal_input.phase
        num_arms = opal_input.num_arms
        
        # Early Termination
        if study_type == StudyType.EARLY_TERMINATION:
            return 8.0
        
        # Phase I studies
        if phase == Phase.PHASE_I:
            if num_arms == 1:
                return 1.0
            else:
                return 2.0
        
        # Observational studies
        if study_type == StudyType.OBSERVATIONAL:
            return 3.0
        
        # Check for procedures
        num_sp = opal_input.num_special_procedures
        num_cp = opal_input.num_complex_procedures
        
        has_procedures = (
            num_sp > 0 or 
            num_cp > 0 or 
            opal_input.has_tissue_biopsy or 
            opal_input.has_pk_draws or 
            opal_input.has_specialized_procedures
        )
        
        if not has_procedures:
            return 3.0
        
        # One procedure type
        if num_sp > 0 and num_cp == 0:
            return 4.0 if num_sp == 1 else 5.0
        
        if num_cp > 0 and num_sp == 0:
            return 4.0 if num_cp == 1 else 5.0
        
        # Multiple procedure types
        if num_sp > 1 and num_cp > 1:
            return 7.0
        
        # Default: moderate complexity
        return 6.0
    
    def _calculate_modifiers(self, opal_input: OPALInput) -> float:
        """
        Calculate OPAL modifier adjustments
        
        Modifiers:
        - Complex assessments: +0.5
        - Tissue biopsy: +0.5
        - PK draws: +0.5
        - Specialized procedures: +0.5
        - Phase III or IV: +0.5
        - Therapeutic area complexity: +0.5 to +1.0
        """
        adjustment = 0.0
        
        # Complex assessments
        if opal_input.has_complex_assessments:
            adjustment += 0.5
        
        # Special procedures
        if opal_input.has_tissue_biopsy:
            adjustment += 0.5
        
        if opal_input.has_pk_draws:
            adjustment += 0.5
        
        if opal_input.has_specialized_procedures:
            adjustment += 0.5
        
        # Phase complexity
        if opal_input.phase in [Phase.PHASE_III, Phase.PHASE_IV]:
            adjustment += 0.5
        
        # Therapeutic area complexity
        if opal_input.therapeutic_area:
            ta_lower = opal_input.therapeutic_area.lower()
            if any(term in ta_lower for term in ['oncology', 'cancer', 'rare disease']):
                adjustment += 1.0
            elif any(term in ta_lower for term in ['cardiovascular', 'neurology', 'psychiatry']):
                adjustment += 0.5
        
        return adjustment
    
    def _distribute_hours(self, total_hours: float) -> Dict[str, Dict[str, float]]:
        """
        Distribute total hours across staff roles by visit type
        
        Args:
            total_hours: Total overhead hours to distribute
            
        Returns:
            Dict of visit_type -> role -> hours
        """
        distribution = {}
        
        for visit_type, role_percentages in self.STAFF_DISTRIBUTION.items():
            distribution[visit_type] = {}
            for role, percentage in role_percentages.items():
                distribution[visit_type][role] = total_hours * percentage
        
        return distribution
    
    def _get_raw_score_reasoning(self, opal_input: OPALInput) -> Dict[str, any]:
        """Get human-readable reasoning for raw score"""
        study_type = opal_input.study_type
        phase = opal_input.phase
        
        reasoning = {
            "study_type": study_type.value if study_type else "Unknown",
            "phase": phase.value if phase else "Unknown",
            "num_arms": opal_input.num_arms,
            "has_procedures": opal_input.num_special_procedures > 0 or opal_input.num_complex_procedures > 0
        }
        
        return reasoning
    
    def _get_modifier_reasoning(self, opal_input: OPALInput) -> List[Dict[str, any]]:
        """Get human-readable list of applied modifiers"""
        modifiers = []
        
        if opal_input.has_complex_assessments:
            modifiers.append({"name": "Complex Assessments", "value": 0.5})
        
        if opal_input.has_tissue_biopsy:
            modifiers.append({"name": "Tissue Biopsy", "value": 0.5})
        
        if opal_input.has_pk_draws:
            modifiers.append({"name": "PK Draws", "value": 0.5})
        
        if opal_input.has_specialized_procedures:
            modifiers.append({"name": "Specialized Procedures", "value": 0.5})
        
        if opal_input.phase in [Phase.PHASE_III, Phase.PHASE_IV]:
            modifiers.append({"name": f"{opal_input.phase.value} Complexity", "value": 0.5})
        
        if opal_input.therapeutic_area:
            ta_lower = opal_input.therapeutic_area.lower()
            if any(term in ta_lower for term in ['oncology', 'cancer', 'rare disease']):
                modifiers.append({"name": f"{opal_input.therapeutic_area} Complexity", "value": 1.0})
            elif any(term in ta_lower for term in ['cardiovascular', 'neurology', 'psychiatry']):
                modifiers.append({"name": f"{opal_input.therapeutic_area} Complexity", "value": 0.5})
        
        return modifiers


# Global singleton
_opal_calculator = None

def get_opal_calculator() -> OPALCalculator:
    """Get or create global OPAL calculator instance"""
    global _opal_calculator
    if _opal_calculator is None:
        _opal_calculator = OPALCalculator()
    return _opal_calculator







