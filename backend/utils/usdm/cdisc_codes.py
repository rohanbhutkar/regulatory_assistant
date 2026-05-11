"""
CDISC Code Resolver
Maps common values to CDISC Controlled Terminology codes
"""

from typing import Dict, Any, Optional


class CDISCCodeResolver:
    """
    Resolves values to CDISC Controlled Terminology codes.
    Provides standardized code objects for USDM entities.
    """
    
    # Phase mappings
    PHASE_CODES = {
        '1': ('C15600', 'PHASE I TRIAL'),
        'phase 1': ('C15600', 'PHASE I TRIAL'),
        'phase i': ('C15600', 'PHASE I TRIAL'),
        'i': ('C15600', 'PHASE I TRIAL'),
        '2': ('C15601', 'PHASE II TRIAL'),
        'phase 2': ('C15601', 'PHASE II TRIAL'),
        'phase ii': ('C15601', 'PHASE II TRIAL'),
        'ii': ('C15601', 'PHASE II TRIAL'),
        '3': ('C15602', 'PHASE III TRIAL'),
        'phase 3': ('C15602', 'PHASE III TRIAL'),
        'phase iii': ('C15602', 'PHASE III TRIAL'),
        'iii': ('C15602', 'PHASE III TRIAL'),
        '4': ('C15603', 'PHASE IV TRIAL'),
        'phase 4': ('C15603', 'PHASE IV TRIAL'),
        'phase iv': ('C15603', 'PHASE IV TRIAL'),
        'iv': ('C15603', 'PHASE IV TRIAL'),
    }
    
    # Study type mappings
    STUDY_TYPE_CODES = {
        'interventional': ('C98388', 'Interventional Study Model'),
        'observational': ('C142615', 'Observational Study Model'),
    }
    
    # Arm type mappings (inferred from name)
    ARM_TYPE_CODES = {
        'experimental': ('C174266', 'Experimental'),
        'active comparator': ('C174265', 'Active Comparator'),
        'placebo': ('C174268', 'Placebo Comparator'),
        'no intervention': ('C174267', 'No Intervention'),
    }
    
    # Objective level mappings
    OBJECTIVE_LEVEL_CODES = {
        'primary': ('C98772', 'Study Primary Objective'),
        'secondary': ('C98781', 'Study Secondary Objective'),
        'exploratory': ('C174238', 'Study Exploratory Objective'),
    }
    
    # Criterion category mappings
    CRITERION_CATEGORY_CODES = {
        'inclusion': ('C25532', 'Inclusion Criterion'),
        'exclusion': ('C25370', 'Exclusion Criterion'),
    }
    
    # Epoch type mappings (inferred from name)
    EPOCH_TYPE_CODES = {
        'screening': ('C99079', 'Screening'),
        'treatment': ('C49676', 'Treatment'),
        'follow-up': ('C71738', 'Follow-up'),
        'washout': ('C50044', 'Washout'),
    }
    
    def __init__(self):
        self.code_system = 'http://www.cdisc.org'
        self.code_system_version = '2024-09-27'
    
    def resolve_phase(self, phase: Optional[str]) -> Dict[str, Any]:
        """
        Resolve study phase to CDISC code.
        
        Args:
            phase: Phase string (e.g., 'Phase 2', '3', 'Phase III')
        
        Returns:
            AliasCode object with standardCode
        """
        if not phase:
            phase = '2'  # Default to Phase 2
        
        phase_key = str(phase).lower().strip()
        code, decode = self.PHASE_CODES.get(phase_key, ('C15601', 'PHASE II TRIAL'))
        
        return self.build_alias_code(code, decode)
    
    def resolve_study_type(self, study_type: Optional[str]) -> Dict[str, Any]:
        """
        Resolve study type to CDISC code.
        
        Args:
            study_type: Study type (e.g., 'Interventional', 'Observational')
        
        Returns:
            Code object
        """
        if not study_type:
            study_type = 'interventional'  # Default
        
        type_key = study_type.lower().strip()
        code, decode = self.STUDY_TYPE_CODES.get(type_key, ('C98388', 'Interventional Study Model'))
        
        return self.build_code(code, decode)
    
    def resolve_arm_type(self, arm_name: str) -> Dict[str, Any]:
        """
        Resolve arm type from arm name (inferred).
        
        Args:
            arm_name: Arm name (e.g., 'Placebo Arm', 'Treatment Arm')
        
        Returns:
            Code object
        """
        name_lower = arm_name.lower()
        
        # Check for specific keywords
        if 'placebo' in name_lower:
            code, decode = ('C174268', 'Placebo Comparator')
        elif 'control' in name_lower or 'comparator' in name_lower:
            code, decode = ('C174265', 'Active Comparator')
        elif 'no intervention' in name_lower:
            code, decode = ('C174267', 'No Intervention')
        else:
            code, decode = ('C174266', 'Experimental')
        
        return self.build_code(code, decode)
    
    def resolve_objective_level(self, level: str) -> Dict[str, Any]:
        """
        Resolve objective level to CDISC code.
        
        Args:
            level: Objective level ('primary', 'secondary', 'exploratory')
        
        Returns:
            Code object
        """
        level_key = level.lower().strip()
        code, decode = self.OBJECTIVE_LEVEL_CODES.get(level_key, ('C98772', 'Study Primary Objective'))
        
        return self.build_code(code, decode)
    
    def resolve_criterion_category(self, category: str) -> Dict[str, Any]:
        """
        Resolve criterion category to CDISC code.
        
        Args:
            category: Criterion type ('inclusion', 'exclusion')
        
        Returns:
            Code object
        """
        category_key = category.lower().strip()
        code, decode = self.CRITERION_CATEGORY_CODES.get(category_key, ('C25532', 'Inclusion Criterion'))
        
        return self.build_code(code, decode)
    
    def resolve_epoch_type(self, epoch_name: str) -> Dict[str, Any]:
        """
        Resolve epoch type from name (inferred).
        
        Args:
            epoch_name: Epoch name (e.g., 'Screening', 'Treatment Period')
        
        Returns:
            Code object
        """
        name_lower = epoch_name.lower()
        
        # Check for specific keywords
        if 'screen' in name_lower:
            code, decode = ('C99079', 'Screening')
        elif 'treatment' in name_lower:
            code, decode = ('C49676', 'Treatment')
        elif 'follow' in name_lower:
            code, decode = ('C71738', 'Follow-up')
        elif 'washout' in name_lower:
            code, decode = ('C50044', 'Washout')
        else:
            code, decode = ('C99079', 'Study Period')
        
        return self.build_code(code, decode)
    
    def build_code(self, code: str, decode: str) -> Dict[str, Any]:
        """
        Build a standard Code object.
        
        Args:
            code: CDISC code (e.g., 'C15601')
            decode: Human-readable term (e.g., 'PHASE II TRIAL')
        
        Returns:
            Code object with all required fields
        """
        return {
            'code': code,
            'codeSystem': self.code_system,
            'codeSystemVersion': self.code_system_version,
            'decode': decode
        }
    
    def build_alias_code(self, code: str, decode: str) -> Dict[str, Any]:
        """
        Build an AliasCode object (used for phase and other aliased codes).
        
        Args:
            code: CDISC code
            decode: Human-readable term
        
        Returns:
            AliasCode object with standardCode
        """
        return {
            'standardCode': self.build_code(code, decode),
            'standardCodeAliases': []
        }








