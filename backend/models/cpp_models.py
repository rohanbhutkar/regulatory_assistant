"""
CPP (Clinical Per-Patient) Data Models
Data models for OPAL, SPU, Procedures, and Rules
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from decimal import Decimal
from enum import Enum


# ===================================================================
# OPAL Models
# ===================================================================

class StudyType(str, Enum):
    """Study type enumeration"""
    INTERVENTIONAL = "Interventional"
    OBSERVATIONAL = "Observational"
    EARLY_TERMINATION = "Early Termination"


class Phase(str, Enum):
    """Study phase enumeration"""
    PHASE_I = "Phase I"
    PHASE_II = "Phase II"
    PHASE_III = "Phase III"
    PHASE_IV = "Phase IV"


@dataclass
class OPALInput:
    """Input data for OPAL calculation"""
    study_type: StudyType
    phase: Phase
    num_arms: int
    therapeutic_area: Optional[str] = None
    has_tissue_biopsy: bool = False
    has_pk_draws: bool = False
    has_specialized_procedures: bool = False
    has_complex_assessments: bool = False
    num_special_procedures: int = 0
    num_complex_procedures: int = 0


@dataclass
class OPALResult:
    """Result of OPAL calculation"""
    raw_score: float
    modifier_score: float
    adjusted_score: float
    total_overhead_hours: float
    staff_distribution: Dict[str, Dict[str, float]]  # visit_type -> role -> hours
    calculation_details: Dict[str, any]


# ===================================================================
# SPU Models
# ===================================================================

@dataclass
class SPUProcedure:
    """SPU Procedure definition"""
    code: str
    description: str
    category: str
    active: bool = True


@dataclass
class SPUPrice:
    """SPU pricing by country"""
    procedure_code: str
    country_code: str
    local_price: Decimal
    currency: str
    effective_date: Optional[str] = None
    source: str = "SPU"


# ===================================================================
# Procedure Models
# ===================================================================

class ProcedureCategory(str, Enum):
    """Procedure category enumeration"""
    QUESTIONNAIRES = "Questionnaires, Scales and Assessments"
    EVALUATION_MANAGEMENT = "Evaluation and Management Services"
    LABORATORY = "Laboratory Testing"
    RADIOLOGY = "Radiology Services"
    MEDICINE = "Medicine Services and Procedures"
    PATHOLOGY = "Pathology and Laboratory"
    SURGERY = "Surgical Procedures"
    ANESTHESIA = "Anesthesia"
    OTHER = "Other"


@dataclass
class Procedure:
    """Clinical procedure definition"""
    code: str
    short_description: str
    long_description: Optional[str] = None
    category: ProcedureCategory = ProcedureCategory.OTHER
    procedure_level: str = "Visit"
    base_price_usd: Optional[Decimal] = None
    active: bool = True


@dataclass
class ProcedureMatch:
    """Result of fuzzy matching"""
    raw_text: str
    normalized_text: str
    matched_code: Optional[str] = None
    matched_description: Optional[str] = None
    confidence_score: float = 0.0
    match_type: str = "none"  # 'exact', 'fuzzy', 'partial', 'none'
    alternatives: List[Dict[str, any]] = field(default_factory=list)
    requires_review: bool = True


# ===================================================================
# Rules Models
# ===================================================================

class RuleType(str, Enum):
    """Rule type enumeration"""
    GOLDEN = "Golden"
    COUNTRY = "Country"
    INDICATION = "Indication"


class RuleAction(str, Enum):
    """Rule action type"""
    ADD_COST = "add_cost"
    MULTIPLY = "multiply"
    ADD_PERCENTAGE = "add_percentage"
    SET_VALUE = "set_value"


@dataclass
class Rule:
    """Business rule definition"""
    id: str
    name: str
    rule_type: RuleType
    description: str
    conditions: Dict[str, any]
    action: RuleAction
    value: float
    priority: int = 0
    active: bool = True


@dataclass
class RuleApplication:
    """Record of rule application"""
    rule_id: str
    rule_name: str
    applied_value: float
    context: Dict[str, any]


# ===================================================================
# CPP Calculation Models
# ===================================================================

@dataclass
class VisitProcedure:
    """Procedure in a visit"""
    visit_name: str
    visit_number: int
    procedure_code: str
    procedure_name: str
    frequency: float = 1.0
    is_optional: bool = False
    probability: float = 1.0


@dataclass
class CPPInput:
    """Input for CPP calculation"""
    indication: str
    phase: Phase
    country_code: str
    procedures: List[VisitProcedure]
    opal_input: OPALInput
    study_context: Optional[Dict[str, any]] = None


@dataclass
class CPPBreakdown:
    """Detailed CPP cost breakdown"""
    direct_procedures: Decimal
    staff_overhead: Decimal
    administration: Decimal
    travel_stipend: Decimal
    other_direct_costs: Decimal
    country_adjustments: Decimal
    total_before_overhead: Decimal
    overhead_percentage: float
    overhead_amount: Decimal
    total_cpp: Decimal


@dataclass
class CPPResult:
    """Complete CPP calculation result"""
    total_cpp: Decimal
    currency: str
    country_code: str
    breakdown: CPPBreakdown
    opal_result: Optional[OPALResult] = None
    procedure_costs: List[Dict[str, any]] = field(default_factory=list)
    rules_applied: List[RuleApplication] = field(default_factory=list)
    matrix_data: Optional[Dict[str, any]] = None
    calculation_metadata: Dict[str, any] = field(default_factory=dict)


# ===================================================================
# Matrix Calculation Models
# ===================================================================

@dataclass
class CostMatrix:
    """Cost matrix (Procedures × Visits)"""
    procedures: List[str]  # Procedure codes
    visits: List[str]  # Visit names
    frequency_matrix: List[List[float]]  # Frequencies
    cost_vector: List[Decimal]  # Cost per procedure
    cost_matrix: List[List[Decimal]]  # Calculated costs
    per_visit_totals: List[Decimal]
    per_procedure_totals: List[Decimal]
    grand_total: Decimal


# ===================================================================
# Helper Functions
# ===================================================================

def to_dict(obj):
    """Convert dataclass to dictionary, handling Decimal conversion"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, Enum):
        return obj.value
    elif hasattr(obj, '__dataclass_fields__'):
        return {
            key: to_dict(value)
            for key, value in obj.__dict__.items()
        }
    elif isinstance(obj, list):
        return [to_dict(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: to_dict(value) for key, value in obj.items()}
    else:
        return obj







