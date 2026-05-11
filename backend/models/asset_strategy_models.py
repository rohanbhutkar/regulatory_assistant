"""
Asset Strategy Models - Extended asset models for Phase 1
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import uuid


class DevelopmentStage(str, Enum):
    DISCOVERY = "discovery"
    PRECLINICAL = "preclinical"
    PHASE_I = "phase_i"
    PHASE_II = "phase_ii"
    PHASE_III = "phase_iii"
    PRE_LAUNCH = "pre_launch"
    LAUNCHED = "launched"


class AssetStatus(str, Enum):
    GO = "go"
    NO_GO = "no_go"
    CONDITIONAL_GO = "conditional_go"
    REVISIT = "revisit"


class DecisionCutStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SUPERSEDED = "superseded"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DELEGATED = "delegated"


class EvidenceArtifactType(str, Enum):
    TPP = "tpp"
    PROTOCOL = "protocol"
    PUBLICATION = "publication"
    SUBMISSION = "submission"


# Extended Asset Model
class AssetStrategy(BaseModel):
    """Extended asset model with strategy fields"""
    id: str
    asset_name: str
    therapeutic_area: str
    indication: Optional[str] = None
    indications: Optional[List[str]] = Field(default_factory=list)  # Multiple indications
    moa: Optional[str] = None  # Mechanism of Action
    roa: Optional[str] = None  # Route of Administration
    subpopulations: Optional[List[str]] = Field(default_factory=list)
    development_stage: Optional[DevelopmentStage] = None
    status: Optional[AssetStatus] = None
    launch_sequence: Optional[List[Dict[str, Any]]] = Field(default_factory=list)  # [{market: "US", sequence: 1}, ...]
    
    # Existing fields
    trial_phase: Optional[str] = None
    cost_per_patient: Optional[float] = None
    total_estimated_cost: Optional[float] = None
    projected_revenue: Optional[float] = None
    current_trials: List[Dict[str, Any]] = Field(default_factory=list)
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = "system"
    
    # Timeline fields
    expected_launch_dates: Optional[Dict[str, str]] = Field(default_factory=dict)  # {market: date}
    key_milestone_dates: Optional[Dict[str, str]] = Field(default_factory=dict)  # {milestone: date}
    
    class Config:
        use_enum_values = True


# Decision Cut Models
class DecisionCut(BaseModel):
    """Immutable snapshot of asset state"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    asset_id: str
    cut_name: str
    cut_description: Optional[str] = None
    frozen_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    frozen_by: str
    snapshot_data: Dict[str, Any]  # Full asset state as JSONB
    previous_cut_id: Optional[str] = None
    status: DecisionCutStatus = DecisionCutStatus.DRAFT
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    class Config:
        use_enum_values = True


class DecisionCutDiff(BaseModel):
    """Comparison result between two decision cuts"""
    cut1_id: str
    cut2_id: str
    changes: Dict[str, Any]  # Field-level changes
    added_items: List[str] = Field(default_factory=list)
    removed_items: List[str] = Field(default_factory=list)
    modified_items: List[str] = Field(default_factory=list)
    impact_assessment: Optional[Dict[str, Any]] = None  # Which calculations need re-run


# Approval Models
class Approval(BaseModel):
    """Approval record for a decision cut"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    decision_cut_id: str
    approver_id: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    comments: Optional[str] = None
    approved_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    class Config:
        use_enum_values = True


class ApprovalRequest(BaseModel):
    """Request for approval"""
    decision_cut_id: str
    required_approvers: List[str]  # List of user IDs
    optional_approvers: Optional[List[str]] = Field(default_factory=list)
    priority: Optional[str] = "normal"  # normal, high, urgent
    notes: Optional[str] = None


# Evidence Artifact Models
class EvidenceArtifact(BaseModel):
    """Evidence document/artifact"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    asset_id: str
    artifact_type: EvidenceArtifactType
    file_name: str
    file_path: str
    file_size: Optional[int] = None
    uploaded_by: str
    uploaded_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    extracted_entities: Optional[Dict[str, Any]] = Field(default_factory=dict)  # {drugs: [...], endpoints: [...]}
    linked_fields: Optional[Dict[str, Any]] = Field(default_factory=dict)  # {indication: "NSCLC", endpoint: "OS"}
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    confidence_score: Optional[float] = None
    
    class Config:
        use_enum_values = True


# Assumption Set Models
class Comparator(BaseModel):
    """Comparator drug information"""
    drug: str
    indication: str
    market: str
    rationale: Optional[str] = None
    source: Optional[str] = None


class AssumptionSet(BaseModel):
    """Assumption set for an asset"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    asset_id: str
    name: str
    is_locked: bool = False
    comparator_set: List[Comparator] = Field(default_factory=list)
    benefit_hypothesis: Optional[str] = None
    uptake_archetype: Optional[str] = None  # 'fast', 'moderate', 'slow'
    uptake_parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    version: int = 1


# Request/Response Models
class CreateAssetRequest(BaseModel):
    asset_name: str
    therapeutic_area: str
    indication: Optional[str] = None
    moa: Optional[str] = None
    roa: Optional[str] = None
    development_stage: Optional[DevelopmentStage] = None
    status: Optional[AssetStatus] = None


class UpdateAssetRequest(BaseModel):
    asset_name: Optional[str] = None
    therapeutic_area: Optional[str] = None
    indication: Optional[str] = None
    indications: Optional[List[str]] = None
    moa: Optional[str] = None
    roa: Optional[str] = None
    subpopulations: Optional[List[str]] = None
    development_stage: Optional[DevelopmentStage] = None
    status: Optional[AssetStatus] = None
    launch_sequence: Optional[List[Dict[str, Any]]] = None
    expected_launch_dates: Optional[Dict[str, str]] = None
    key_milestone_dates: Optional[Dict[str, str]] = None


class CreateDecisionCutRequest(BaseModel):
    asset_id: str
    cut_name: str
    cut_description: Optional[str] = None
    required_approvers: List[str]
    notes: Optional[str] = None


class ApproveDecisionCutRequest(BaseModel):
    approval_id: str
    comments: Optional[str] = None


class RejectDecisionCutRequest(BaseModel):
    approval_id: str
    comments: str  # Required for rejection


class CreateAssumptionSetRequest(BaseModel):
    asset_id: str
    name: str
    comparator_set: Optional[List[Comparator]] = Field(default_factory=list)
    benefit_hypothesis: Optional[str] = None
    uptake_archetype: Optional[str] = None
    uptake_parameters: Optional[Dict[str, Any]] = Field(default_factory=dict)


class UpdateAssumptionSetRequest(BaseModel):
    comparator_set: Optional[List[Comparator]] = None
    benefit_hypothesis: Optional[str] = None
    uptake_archetype: Optional[str] = None
    uptake_parameters: Optional[Dict[str, Any]] = None


# Structured Generation Response Models
class SubpopulationsResponse(BaseModel):
    """Structured response for subpopulations generation"""
    subpopulations: List[str] = Field(..., description="List of patient subpopulations")


class IndicationsResponse(BaseModel):
    """Structured response for indications generation"""
    indications: List[str] = Field(..., description="List of relevant indications")


class MoAResponse(BaseModel):
    """Structured response for MoA generation"""
    moa: str = Field(..., description="Detailed mechanism of action description")


class ComparatorsResponse(BaseModel):
    """Structured response for comparators generation"""
    comparators: List[Dict[str, str]] = Field(..., description="List of comparators with drug, indication, market, and rationale")


class BenefitHypothesisResponse(BaseModel):
    """Structured response for benefit hypothesis generation"""
    benefit_hypothesis: str = Field(..., description="Comprehensive benefit hypothesis in markdown format")
    key_differentiators: List[str] = Field(default_factory=list, description="Key differentiators vs comparators")
    value_proposition: str = Field(default="", description="Clinical value proposition")


class AssumptionSetResponse(BaseModel):
    """Structured response for assumption set generation"""
    comparators: List[Dict[str, str]] = Field(..., description="List of comparators")
    benefit_hypothesis: str = Field(..., description="Benefit hypothesis in markdown format")
    key_differentiators: List[str] = Field(default_factory=list, description="Key differentiators")
    value_proposition: str = Field(default="", description="Value proposition")
    market_assumptions: Dict[str, Any] = Field(default_factory=dict, description="Market assumptions")
    clinical_assumptions: Dict[str, Any] = Field(default_factory=dict, description="Clinical assumptions")


class PricingParametersResponse(BaseModel):
    """Structured response for pricing parameters"""
    list_price_range: Dict[str, float] = Field(..., description="Min and max list price")
    expected_rebate_pct: float = Field(..., description="Expected rebate percentage (0-100)")
    net_price_estimate: float = Field(..., description="Estimated net price")
    pricing_strategy: str = Field(..., description="Pricing strategy recommendations")
    rationale: str = Field(default="", description="Rationale for pricing recommendations")


class TimelineRecommendationsResponse(BaseModel):
    """Structured response for timeline recommendations"""
    success: bool = Field(default=True, description="Whether the generation was successful")
    expected_launch_dates: Dict[str, str] = Field(default_factory=dict, description="Recommended launch dates by market (YYYY-MM-DD format)")
    key_milestone_dates: Dict[str, str] = Field(default_factory=dict, description="Recommended milestone dates (YYYY-MM-DD format)")
    rationale: str = Field(default="", description="Rationale for timeline recommendations")
    historical_context: str = Field(default="", description="Historical submission timeline context used")
    confidence: str = Field(default="Medium", description="Confidence level: High/Medium/Low")
    considerations: str = Field(default="", description="Key considerations, assumptions, and factors impacting timelines (e.g., JCA impact for EU, regulatory changes, etc.)")

