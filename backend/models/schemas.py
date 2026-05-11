"""
Pydantic schemas for the Clinical Research Assistant
"""
from datetime import datetime
from typing import List, Dict, Any, Optional, Set, Union
from pydantic import BaseModel, Field, field_validator

class QueryRequest(BaseModel):
    query: str = Field(..., description="Clinical research question")
    sources: Optional[List[str]] = Field(
        default=["clinical_trials", "pubmed", "biomcp", "aact", "fierce_pharma"],
        description="Data sources to search"
    )
    max_results: Optional[int] = Field(
        default=50,
        description="Maximum number of results per source"
    )
    include_full_text: Optional[bool] = Field(
        default=False,
        description="Include full text content"
    )

class ClinicalTrialResult(BaseModel):
    nct_id: str = Field(..., description="NCT identifier")
    title: str = Field(..., description="Study title")
    condition: Optional[str] = Field(None, description="Medical condition")
    intervention: Optional[str] = Field(None, description="Intervention type")
    sponsor: Optional[str] = Field(None, description="Study sponsor")
    status: Optional[str] = Field(None, description="Study status")
    phase: Optional[str] = Field(None, description="Clinical trial phase")
    enrollment: Optional[int] = Field(None, description="Enrollment count")
    start_date: Optional[str] = Field(None, description="Study start date")
    completion_date: Optional[str] = Field(None, description="Study completion date")
    description: Optional[str] = Field(None, description="Study description")
    location: Optional[str] = Field(None, description="Study location (legacy field)")
    relevance_score: Optional[float] = Field(None, description="Relevance score")
    # Flexible metadata field to capture all additional AACT data
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Additional metadata from AACT database (facilities, sponsors, outcomes, etc.)"
    )

# Unified Trial Data Model for HITL Integration
class UnifiedTrialResult(BaseModel):
    """Unified trial data model that standardizes data from all sources"""
    nct_id: str = Field(..., description="NCT identifier")
    title: str = Field(..., description="Study title")
    condition: Optional[str] = Field(None, description="Medical condition")
    intervention: Optional[str] = Field(None, description="Intervention type")
    sponsor: Optional[str] = Field(None, description="Study sponsor")
    status: Optional[str] = Field(None, description="Study status")
    phase: Optional[str] = Field(None, description="Clinical trial phase")
    enrollment: Optional[int] = Field(None, description="Enrollment count")
    start_date: Optional[str] = Field(None, description="Study start date")
    completion_date: Optional[str] = Field(None, description="Study completion date")
    description: Optional[str] = Field(None, description="Study description")
    location: Optional[str] = Field(None, description="Study location")
    
    # Source identification
    source: str = Field(..., description="Data source: 'aact', 'trialtrove', 'clinical_trials'")
    
    # HITL-specific fields
    relevance_score: Optional[float] = Field(None, description="AI-calculated relevance score")
    selection_reason: Optional[str] = Field(None, description="AI explanation for selection")
    is_selected: bool = Field(False, description="Whether trial was selected by human")
    selection_timestamp: Optional[str] = Field(None, description="When trial was selected")
    
    # Scoring breakdown for transparency
    scores: Optional[Dict[str, float]] = Field(
        default_factory=dict,
        description="Detailed scoring breakdown (query_relevance, therapeutic_area, etc.)"
    )
    
    # Detailed trial information
    inclusion_criteria: Optional[str] = Field(None, description="Inclusion criteria")
    exclusion_criteria: Optional[str] = Field(None, description="Exclusion criteria")
    primary_endpoints: Optional[List[str]] = Field(None, description="Primary endpoints")
    secondary_endpoints: Optional[List[str]] = Field(None, description="Secondary endpoints")
    study_type: Optional[str] = Field(None, description="Study type (interventional, observational)")
    allocation: Optional[str] = Field(None, description="Allocation method")
    masking: Optional[str] = Field(None, description="Masking/blinding information")
    primary_purpose: Optional[str] = Field(None, description="Primary purpose")
    study_population: Optional[str] = Field(None, description="Study population description")
    
    # Flexible metadata field
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        description="Additional metadata from source database"
    )
    
    @classmethod
    def from_clinical_trial_result(cls, trial: 'ClinicalTrialResult', source: str) -> 'UnifiedTrialResult':
        """Convert ClinicalTrialResult to UnifiedTrialResult"""
        return cls(
            nct_id=trial.nct_id,
            title=trial.title,
            condition=trial.condition,
            intervention=trial.intervention,
            sponsor=trial.sponsor,
            status=trial.status,
            phase=trial.phase,
            enrollment=trial.enrollment,
            start_date=trial.start_date,
            completion_date=trial.completion_date,
            description=trial.description,
            location=trial.location,
            source=source,
            relevance_score=trial.relevance_score,
            inclusion_criteria=getattr(trial, 'inclusion_criteria', None),
            exclusion_criteria=getattr(trial, 'exclusion_criteria', None),
            primary_endpoints=getattr(trial, 'primary_endpoints', None),
            secondary_endpoints=getattr(trial, 'secondary_endpoints', None),
            study_type=getattr(trial, 'study_type', None),
            allocation=getattr(trial, 'allocation', None),
            masking=getattr(trial, 'masking', None),
            primary_purpose=getattr(trial, 'primary_purpose', None),
            study_population=getattr(trial, 'study_population', None),
            metadata=trial.metadata or {}
        )
    
    @classmethod
    def from_dict(cls, trial_dict: Dict[str, Any], source: str) -> 'UnifiedTrialResult':
        """Convert dictionary to UnifiedTrialResult"""
        return cls(
            nct_id=trial_dict.get('nct_id', ''),
            title=trial_dict.get('title', ''),
            condition=trial_dict.get('condition'),
            intervention=trial_dict.get('intervention'),
            sponsor=trial_dict.get('sponsor'),
            status=trial_dict.get('status'),
            phase=trial_dict.get('phase'),
            enrollment=trial_dict.get('enrollment'),
            start_date=trial_dict.get('start_date'),
            completion_date=trial_dict.get('completion_date'),
            description=trial_dict.get('description'),
            location=trial_dict.get('location'),
            source=source,
            relevance_score=trial_dict.get('relevance_score'),
            inclusion_criteria=trial_dict.get('inclusion_criteria'),
            exclusion_criteria=trial_dict.get('exclusion_criteria'),
            primary_endpoints=trial_dict.get('primary_endpoints'),
            secondary_endpoints=trial_dict.get('secondary_endpoints'),
            study_type=trial_dict.get('study_type'),
            allocation=trial_dict.get('allocation'),
            masking=trial_dict.get('masking'),
            primary_purpose=trial_dict.get('primary_purpose'),
            study_population=trial_dict.get('study_population'),
            metadata=trial_dict.get('metadata', {})
        )

# HITL-specific schemas
class TrialSuggestion(BaseModel):
    """AI-generated trial suggestion with explanation"""
    trial: UnifiedTrialResult
    suggestion_rank: int = Field(..., description="Ranking in AI suggestions (1-5)")
    explanation: str = Field(..., description="AI explanation for suggestion")
    confidence_score: float = Field(..., description="AI confidence in suggestion (0-1)")

class TrialSelectionState(BaseModel):
    """State for HITL trial selection process"""
    execution_id: str = Field(..., description="Unique execution identifier")
    query: str = Field(..., description="Original search query")
    total_trials: int = Field(..., description="Total number of trials found")
    suggestions: List[TrialSuggestion] = Field(default_factory=list, description="AI suggestions")
    all_trials: List[UnifiedTrialResult] = Field(default_factory=list, description="All available trials")
    selected_trials: List[str] = Field(default_factory=list, description="NCT IDs of selected trials")
    timeout_at: Optional[str] = Field(None, description="Timeout timestamp")
    status: str = Field("pending", description="Selection status: pending, completed, timeout")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = Field(None, description="Completion timestamp")

class PublicationResult(BaseModel):
    pmid: Optional[str] = Field(None, description="PubMed ID")
    pmcid: Optional[str] = Field(None, description="PubMed Central ID")
    title: str = Field(..., description="Publication title")
    authors: Optional[List[str]] = Field(None, description="Author list")
    journal: Optional[str] = Field(None, description="Journal name")
    publication_date: Optional[str] = Field(None, description="Publication date")
    abstract: Optional[str] = Field(None, description="Abstract text")
    keywords: Optional[List[str]] = Field(None, description="Keywords")
    doi: Optional[str] = Field(None, description="DOI")
    full_text: Optional[str] = Field(None, description="Full text content")
    relevance_score: Optional[float] = Field(None, description="Relevance score")

class BioMCPResult(BaseModel):
    id: str = Field(..., description="BioMCP identifier")
    title: str = Field(..., description="Resource title")
    description: Optional[str] = Field(None, description="Resource description")
    type: Optional[str] = Field(None, description="Resource type")
    url: Optional[str] = Field(None, description="Resource URL")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    relevance_score: Optional[float] = Field(None, description="Relevance score")

class OpenFDAResult(BaseModel):
    application_number: Optional[str] = Field(None, description="NDA, ANDA, or BLA number")
    brand_name: Optional[List[str]] = Field(None, description="Brand or trade name of the drug")
    generic_name: Optional[List[str]] = Field(None, description="Generic name of the drug")
    manufacturer_name: Optional[List[str]] = Field(None, description="Manufacturer name")
    dosage_form: Optional[str] = Field(None, description="Drug dosage form")
    route: Optional[str] = Field(None, description="Route of administration")
    marketing_status: Optional[str] = Field(None, description="Marketing status (Prescription/OTC/Discontinued)")
    active_ingredients: Optional[List[Dict[str, str]]] = Field(None, description="Active ingredients and strengths")
    pharm_class_epc: Optional[List[str]] = Field(None, description="Established pharmacologic class")
    pharm_class_moa: Optional[List[str]] = Field(None, description="Mechanism of action")
    pharm_class_pe: Optional[List[str]] = Field(None, description="Physiologic effect")
    sponsor_name: Optional[str] = Field(None, description="Sponsor company name")
    product_ndc: Optional[List[str]] = Field(None, description="Product NDC codes")
    package_ndc: Optional[List[str]] = Field(None, description="Package NDC codes")
    substance_name: Optional[List[str]] = Field(None, description="Active substance names")
    unii: Optional[List[str]] = Field(None, description="Unique Ingredient Identifiers")
    rxcui: Optional[List[str]] = Field(None, description="RxNorm Concept Unique Identifiers")
    relevance_score: Optional[float] = Field(None, description="Relevance score")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional FDA metadata")


class EmaQueryFacets(BaseModel):
    """Structured facets for EMA / EU medicines search routing."""

    product_terms: List[str] = Field(default_factory=list, description="Brand or product name tokens")
    company_terms: List[str] = Field(
        default_factory=list,
        description="Marketing authorisation holder / sponsor name fragments (e.g. boehringer, ingelheim). When non-empty, rows must match at least one in MAH/product text.",
    )
    inn: Optional[str] = Field(None, description="INN / active substance")
    ema_product_number: Optional[str] = Field(None, description="EMA product number if stated")
    pms_id: Optional[str] = Field(None, description="PMS product id if stated")
    gtin: Optional[str] = Field(None, description="GTIN / data carrier if stated")
    atc_code: Optional[str] = Field(None, description="ATC code if stated")
    intent: str = Field(
        "general",
        description="product_profile | epar_documents | post_auth_variation | guidance | shortage | orphan | referral | dhpc | psusa | pip | non_epar_documents | general",
    )


class EmaSearchResult(BaseModel):
    """Unified hit from EMA public JSON feeds, ePI FHIR, or optional PMS read."""

    title: str = Field(..., description="Display title")
    sub_source: str = Field(
        ...,
        description="epi_fhir | medicines_catalog | post_authorisation | epar_documents | non_epar_documents | all_documents | guidance_pages | dhpc | psusa | pip | orphan_designations | shortages | referrals | pms_fhir_read",
    )
    excerpt: str = Field("", description="Short text for synthesis")
    relevance_score: float = Field(0.0, description="Ranking score")
    ema_product_number: Optional[str] = None
    source_urls: List[str] = Field(default_factory=list)
    limitations: Optional[str] = Field(None, description="Coverage or API caveat for this hit")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Raw fields subset / ids")


class ChinaRegulatoryResult(BaseModel):
    """Hit from CDE / NMPA / zwfw discovery (Google CSE + HTML text extraction)."""

    url: str = Field(..., description="Page URL")
    title: str = Field(..., description="Derived title")
    content: str = Field(..., description="Extracted visible text (truncated)")
    source_domain: str = Field(..., description="Host")
    relevance_score: Optional[float] = Field(None, description="Heuristic relevance vs query")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="portal (cde|nmpa_root|zwfw|unknown), original_language, optional content_en",
    )


class LiveDataSearchResult(BaseModel):
    """Normalized hit for live HTTP API agents (NIH Reporter, OpenAlex, CMS, etc.)."""

    url: str = Field(..., description="Canonical or best link for the record")
    title: str = Field(..., description="Display title")
    content: str = Field(
        "",
        description="Text excerpt or JSON summary for synthesis (truncated upstream)",
    )
    source_domain: str = Field(..., description="Logical source label (e.g. api.reporter.nih.gov)")
    relevance_score: Optional[float] = Field(None, description="Optional rank score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Raw ids and typed fields")


class FiercePharmaResult(BaseModel):
    url: str = Field(..., description="Article URL")
    title: str = Field(..., description="Article title")
    content: str = Field(..., description="Article content (truncated)")
    publication_date: Optional[str] = Field(None, description="Publication date")
    companies: List[str] = Field(default_factory=list, description="Mentioned pharmaceutical companies")
    drugs: List[str] = Field(default_factory=list, description="Mentioned drug names")
    topics: List[str] = Field(default_factory=list, description="Key topics discussed")
    relevance_score: Optional[float] = Field(None, description="Relevance score")
    source_domain: str = Field(..., description="Source domain")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

# AACT Database Schemas
class AACTTableInfo(BaseModel):
    name: str = Field(..., description="Table name")
    description: str = Field(..., description="Table description")
    total_studies: Optional[int] = Field(None, description="Total studies in table")
    column_count: Optional[int] = Field(None, description="Number of columns")

class AACTQueryResult(BaseModel):
    success: bool = Field(..., description="Query success status")
    error: Optional[str] = Field(None, description="Error message if failed")
    results: List[Dict[str, Any]] = Field(..., description="Query results")
    row_count: int = Field(..., description="Number of rows returned")

class AACTStudyDetails(BaseModel):
    nct_id: str = Field(..., description="NCT identifier")
    title: str = Field(..., description="Study title")
    conditions: List[str] = Field(default_factory=list, description="Study conditions")
    interventions: List[str] = Field(default_factory=list, description="Study interventions")
    facilities: List[str] = Field(default_factory=list, description="Study facilities")
    outcomes: List[str] = Field(default_factory=list, description="Study outcomes")
    eligibility: Dict[str, Any] = Field(default_factory=dict, description="Eligibility criteria")
    design: Dict[str, Any] = Field(default_factory=dict, description="Study design")
    sponsors: List[str] = Field(default_factory=list, description="Study sponsors")
    documents: List[str] = Field(default_factory=list, description="Study documents")
    references: List[str] = Field(default_factory=list, description="Study references")

class SynthesisResult(BaseModel):
    summary: str = Field(..., description="Synthesized summary")
    key_findings: List[str] = Field(..., description="Key findings")
    recommendations: List[str] = Field(..., description="Recommendations")
    confidence_score: Optional[float] = Field(None, description="Confidence in synthesis")

class QueryMetadata(BaseModel):
    query_timestamp: datetime = Field(..., description="Query timestamp")
    sources_used: List[str] = Field(..., description="Sources actually used")
    processing_time: float = Field(..., description="Processing time in seconds")
    cache_hit: bool = Field(..., description="Whether result was from cache")
    total_results: int = Field(..., description="Total results found")

# New classes for the reasoning engine
class QueryResults(BaseModel):
    clinical_trials: List[Dict[str, Any]] = Field(default_factory=list, description="Clinical trials results")
    publications: List[Dict[str, Any]] = Field(default_factory=list, description="Publications results")
    biomcp_data: List[Dict[str, Any]] = Field(default_factory=list, description="BioMCP data results")
    aact_data: List[Dict[str, Any]] = Field(default_factory=list, description="AACT database results")
    openfda_data: List[Dict[str, Any]] = Field(default_factory=list, description="OpenFDA drug information results")
    fierce_pharma_data: List[Dict[str, Any]] = Field(default_factory=list, description="Fierce Pharma industry news results")

class CitationLink(BaseModel):
    """Frontend-friendly citation with optional hyperlink."""

    text: str = Field(..., description="Short label or full citation line for display")
    url: str = Field(default="", description="Canonical URL when available")


class Synthesis(BaseModel):
    answer: str = Field(..., description="Comprehensive answer with embedded citations")
    citations: List[CitationLink] = Field(
        default_factory=list,
        description="Structured citations with URLs for the UI",
    )
    confidence: str = Field(..., description="Confidence level (high|medium|low)")
    data_quality: str = Field(..., description="Assessment of data quality and completeness")

    @field_validator("citations", mode="before")
    @classmethod
    def _coerce_synthesis_citations(cls, v: Any) -> Any:
        from utils.citation_links import normalize_citation_entries

        return normalize_citation_entries(v)

class Metadata(BaseModel):
    query_timestamp: float = Field(..., description="Query timestamp")
    sources_used: List[str] = Field(default_factory=list, description="Sources used")
    processing_time: float = Field(..., description="Processing time in seconds")
    total_results: int = Field(default=0, description="Total results found")
    deep_research_run_id: Optional[str] = Field(None, description="Deep research run UUID for WebSocket correlation")
    deep_research_replan_rounds: int = Field(0, description="Number of replan rounds executed")
    deep_research_verifier_passed: Optional[bool] = Field(
        None, description="Whether the coverage verifier passed on last check"
    )
    deep_research_parallel_subruns: int = Field(
        0, description="Number of parallel breadth sub-runs merged"
    )

class QueryResponse(BaseModel):
    query_results: QueryResults = Field(..., description="Results from each source")
    synthesis: Synthesis = Field(..., description="Synthesized results")
    metadata: Metadata = Field(..., description="Query metadata")

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")

class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    version: str = Field(..., description="API version")
    cache_status: str = Field(..., description="Cache connection status")
    rate_limiter_status: Dict[str, Dict] = Field(..., description="Rate limiter status")

class APIStatsResponse(BaseModel):
    total_queries: int = Field(..., description="Total queries processed")
    cache_hit_rate: float = Field(..., description="Cache hit rate percentage")
    average_response_time: float = Field(..., description="Average response time")
    api_call_stats: Dict[str, Dict] = Field(..., description="API call statistics")

# New schemas for dynamic graph-based queries
class ConversationMessage(BaseModel):
    """A message in the conversation history"""
    role: str = Field(..., description="Role of the message sender (user|assistant)")
    content: str = Field(..., description="Message content")
    timestamp: Optional[float] = Field(None, description="Message timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")

class DynamicQueryRequest(BaseModel):
    query: str = Field(..., description="Free text query for dynamic graph construction")
    conversation_history: Optional[List[ConversationMessage]] = Field(
        default_factory=list,
        description="Previous conversation messages for context"
    )
    include_graph_plan: Optional[bool] = Field(
        default=False,
        description="Include the generated graph plan in response"
    )
    max_execution_steps: Optional[int] = Field(
        default=48,
        description="Maximum number of execution steps in the graph (aligns with expanded multi-node plans)"
    )

# Enhanced Context Management Schemas
class ContextItem(BaseModel):
    """Individual context item with metadata and relationships"""
    id: str = Field(..., description="Unique context item identifier")
    content: Any = Field(..., description="The actual content/data")
    source: str = Field(..., description="Source of this context item")
    node_id: Optional[str] = Field(None, description="Node that generated this context")
    timestamp: float = Field(..., description="When this context was created")
    relevance_score: Optional[float] = Field(None, description="Relevance to the query")
    context_type: str = Field(..., description="Type of context (raw_data, analysis, reasoning, synthesis)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    relationships: List[str] = Field(default_factory=list, description="IDs of related context items")
    attention_weight: Optional[float] = Field(None, description="Attention weight for synthesis")

class ContextLayer(BaseModel):
    """A layer of context with specific focus"""
    layer_id: str = Field(..., description="Unique layer identifier")
    layer_type: str = Field(..., description="Type of layer (search, analysis, reasoning, synthesis)")
    items: List[ContextItem] = Field(default_factory=list, description="Context items in this layer")
    summary: Optional[str] = Field(None, description="Summary of this layer")
    importance_score: float = Field(default=0.5, description="Overall importance of this layer")

class ContextManager(BaseModel):
    """Manages context throughout the execution graph"""
    query: str = Field(..., description="Original query")
    layers: List[ContextLayer] = Field(default_factory=list, description="Context layers")
    global_context: Dict[str, Any] = Field(default_factory=dict, description="Global context information")
    execution_trace: List[Dict[str, Any]] = Field(default_factory=list, description="Execution trace")
    context_graph: Dict[str, List[str]] = Field(default_factory=dict, description="Context item relationships")
    
    def add_context_item(self, layer_type: str, content: Any, source: str, node_id: str = None, 
                        metadata: Dict[str, Any] = None, relationships: List[str] = None) -> str:
        """Add a new context item to the appropriate layer"""
        import time
        import uuid
        
        # Find or create the appropriate layer
        layer = next((l for l in self.layers if l.layer_type == layer_type), None)
        if not layer:
            layer = ContextLayer(
                layer_id=f"{layer_type}_{len(self.layers)}",
                layer_type=layer_type,
                items=[],
                importance_score=0.5
            )
            self.layers.append(layer)
        
        # Create context item
        item_id = str(uuid.uuid4())
        context_item = ContextItem(
            id=item_id,
            content=content,
            source=source,
            node_id=node_id,
            timestamp=time.time(),
            context_type=layer_type,
            metadata=metadata or {},
            relationships=relationships or []
        )
        
        layer.items.append(context_item)
        
        # Update context graph
        if relationships:
            self.context_graph[item_id] = relationships
        
        return item_id
    
    def get_context_for_synthesis(
        self,
        max_items_per_layer: int = 24,
        layer_char_budget: int = 96000,
        compact_nct_ids: Optional[Union[Set[str], frozenset]] = None,
        bm25_pool_factor: int = 1,
    ) -> str:
        """Get formatted context for synthesis with attention-based selection and per-layer char budget."""
        compact_nct_ids = set(compact_nct_ids) if compact_nct_ids else set()
        context_parts = []
        
        # Add query context
        context_parts.append(f"ORIGINAL QUERY: {self.query}")
        context_parts.append(f"CONTEXT SUMMARY: {len(self.layers)} layers with {sum(len(l.items) for l in self.layers)} total items")
        
        from context_retrieval import rank_items_by_query

        # Process each layer with attention-based selection
        for layer in self.layers:
            if not layer.items:
                continue
                
            context_parts.append(f"\n{layer.layer_type.upper()} LAYER ({len(layer.items)} items):")
            
            if bm25_pool_factor > 1:
                pool_n = min(len(layer.items), max(1, max_items_per_layer * bm25_pool_factor))
                pool = rank_items_by_query(self.query, list(layer.items))[:pool_n]
                sorted_items = sorted(
                    pool,
                    key=lambda x: (x.attention_weight or 0, x.relevance_score or 0),
                    reverse=True,
                )
            else:
                sorted_items = sorted(
                    layer.items,
                    key=lambda x: (x.attention_weight or 0, x.relevance_score or 0),
                    reverse=True,
                )
            
            # Take top items based on attention
            selected_items = sorted_items[:max_items_per_layer]
            remain = max(layer_char_budget, 500)
            
            for i, item in enumerate(selected_items):
                if remain < 120:
                    context_parts.append(
                        "  [Additional items omitted in this layer: character budget exhausted]"
                    )
                    break
                meta_lines = 0
                if item.relationships:
                    meta_lines += 1
                if item.attention_weight is not None:
                    meta_lines += 1
                if item.relevance_score is not None:
                    meta_lines += 1
                reserve = 80 * meta_lines + 40
                body_budget = max(200, remain - reserve)
                formatted = self._format_context_item(
                    item,
                    max_body_chars=body_budget,
                    compact_nct_ids=compact_nct_ids,
                )
                block = f"  {i+1}. {formatted}"
                context_parts.append(block)
                remain -= len(block) + 1
                
                # Add relationship information
                if item.relationships:
                    related_items = [rel for rel in item.relationships if rel in self.context_graph]
                    if related_items:
                        rel_line = f"     Related to: {len(related_items)} other items"
                        context_parts.append(rel_line)
                        remain -= len(rel_line) + 1
                
                # Add attention and relevance scores
                if item.attention_weight:
                    aw = f"     Attention Weight: {item.attention_weight:.3f}"
                    context_parts.append(aw)
                    remain -= len(aw) + 1
                if item.relevance_score:
                    rs = f"     Relevance Score: {item.relevance_score:.3f}"
                    context_parts.append(rs)
                    remain -= len(rs) + 1
        
        return "\n".join(context_parts)
    
    def _format_context_item(
        self,
        item: ContextItem,
        max_body_chars: int | None = None,
        compact_nct_ids: Optional[Union[Set[str], frozenset]] = None,
    ) -> str:
        """Format a context item for synthesis; preserves stable IDs outside truncated prose."""
        compact_nct_ids = set(compact_nct_ids) if compact_nct_ids else set()
        cap = max_body_chars if max_body_chars is not None else 80_000

        def clip(text: str, budget: int, label: str) -> str:
            if budget <= 0:
                return f"{label}: [omitted]"
            s = str(text or "")
            if len(s) <= budget:
                return f"{label}: {s}"
            return f"{label}: {s[: max(0, budget - 20)]}... [{len(s) - max(0, budget - 20)} chars omitted]"

        if isinstance(item.content, dict):
            # Handle different content types
            if 'nct_id' in item.content:
                nct = str(item.content.get('nct_id') or '')
                if nct and nct in compact_nct_ids:
                    return (
                        f"Clinical Trial (NCT: {nct}) — full trial fields appear under "
                        f"STRUCTURED_TRIAL_AND_SOA_DATA in the synthesis prompt; "
                        f"title: {item.content.get('title', 'No title')}"
                    )
                # Format clinical trial data with full metadata (metadata may be capped)
                trial_info = f"Clinical Trial: {item.content.get('title', 'No title')} (NCT: {nct})"
                details = []
                if item.content.get('condition'):
                    details.append(f"Condition: {item.content.get('condition')}")
                if item.content.get('intervention'):
                    details.append(f"Intervention: {item.content.get('intervention')}")
                if item.content.get('sponsor'):
                    details.append(f"Sponsor: {item.content.get('sponsor')}")
                if item.content.get('status'):
                    details.append(f"Status: {item.content.get('status')}")
                if item.content.get('phase'):
                    details.append(f"Phase: {item.content.get('phase')}")
                if item.content.get('enrollment'):
                    details.append(f"Enrollment: {item.content.get('enrollment')}")
                if item.content.get('start_date'):
                    details.append(f"Start Date: {item.content.get('start_date')}")
                if item.content.get('completion_date'):
                    details.append(f"Completion Date: {item.content.get('completion_date')}")

                meta_budget = max(0, cap - len(trial_info) - 48)
                metadata = item.content.get('metadata', {})
                if metadata and meta_budget > 80:
                    details.append("Additional AACT Data:")
                    used = 0
                    for key, value in metadata.items():
                        if value is None or not str(value).strip():
                            continue
                        formatted_key = key.replace('_', ' ').title()
                        chunk = f"  {formatted_key}: {value}"
                        if used + len(chunk) > meta_budget:
                            details.append(f"  ... [{len(metadata)} metadata keys; more omitted]")
                            break
                        details.append(chunk)
                        used += len(chunk)

                if details:
                    trial_info += "\n     " + "\n   ".join(details)

                if len(trial_info) > cap:
                    head = trial_info[: max(0, cap - 40)]
                    return head + "... [trial row truncated]"
                return trial_info

            elif 'pmid' in item.content:
                t = item.content.get('title', 'No title')
                pmid = item.content.get('pmid')
                base = f"Publication: {t} (PMID: {pmid})"
                if len(base) <= cap:
                    return base
                return base[: max(0, cap - 30)] + "... [truncated]"

            elif item.content.get("compression_brief"):
                cb_raw = item.content.get("compression_brief")
                try:
                    import json

                    from context_compression import CompressionBrief

                    data = json.loads(cb_raw) if isinstance(cb_raw, str) else cb_raw
                    brief = CompressionBrief.model_validate(data)
                    pretty = brief.model_dump_json(indent=2)
                    return clip(pretty, cap, "Compressed analysis brief")
                except Exception:
                    return clip(str(cb_raw), cap, "Compressed analysis brief")

            elif 'analysis' in item.content:
                return clip(str(item.content.get('analysis', '')), cap, "Analysis")

            elif 'reasoning' in item.content:
                return clip(str(item.content.get('reasoning', '')), cap, "Reasoning")

            else:
                return clip(str(item.content), max(cap, 400), "Data")
        else:
            return clip(str(item.content), cap, "Content")
    
    def calculate_attention_weights(
        self,
        query_keywords: List[str] = None,
        *,
        method: str = "keyword",
        hybrid_keyword_weight: float = 0.35,
    ):
        """Calculate attention weights: keyword overlap, BM25 over full query, or hybrid."""
        import re

        from utils.bm25 import bm25_scores, normalize_scores

        if not query_keywords:
            query_keywords = re.findall(r"\b\w+\b", self.query.lower())

        for layer in self.layers:
            if not layer.items:
                continue
            docs = [str(it.content) for it in layer.items]

            if method == "bm25":
                ns = normalize_scores(bm25_scores(self.query, docs))
                for item, score in zip(layer.items, ns):
                    item.attention_weight = float(score)
                continue

            if method == "hybrid":
                ns = normalize_scores(bm25_scores(self.query, docs))
                w_k = max(0.0, min(1.0, hybrid_keyword_weight))
                for item, bscore in zip(layer.items, ns):
                    content_text = str(item.content).lower()
                    keyword_matches = (
                        sum(1 for keyword in query_keywords if keyword in content_text)
                        if query_keywords
                        else 0
                    )
                    kw_part = (
                        min(1.0, keyword_matches / len(query_keywords)) if query_keywords else 0.5
                    )
                    item.attention_weight = w_k * kw_part + (1.0 - w_k) * float(bscore)
                continue

            for item in layer.items:
                content_text = str(item.content).lower()
                keyword_matches = sum(1 for keyword in query_keywords if keyword in content_text)
                item.attention_weight = (
                    min(1.0, keyword_matches / len(query_keywords)) if query_keywords else 0.5
                )

class GraphNode(BaseModel):
    id: str = Field(..., description="Unique node identifier")
    type: str = Field(..., description="Node type (search, analyze, synthesize, etc.)")
    description: str = Field(..., description="Node description")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Node parameters")
    dependencies: List[str] = Field(default_factory=list, description="Dependent node IDs")

class GraphPlan(BaseModel):
    nodes: List[GraphNode] = Field(..., description="Graph nodes")
    edges: List[Dict[str, str]] = Field(..., description="Graph edges")
    execution_order: List[str] = Field(..., description="Planned execution order")
    reasoning: str = Field(..., description="Reasoning for graph construction")

class DynamicQueryResponse(BaseModel):
    query: str = Field(..., description="Original query")
    graph_plan: Optional[GraphPlan] = Field(None, description="Generated graph plan")
    results: Dict[str, Any] = Field(..., description="Execution results")
    synthesis: Synthesis = Field(..., description="Final synthesis")
    metadata: Metadata = Field(..., description="Query metadata")
    execution_trace: List[Dict[str, Any]] = Field(default_factory=list, description="Execution trace")
    context_manager: Optional[ContextManager] = Field(None, description="Enhanced context management")

class SimpleQueryResponse(BaseModel):
    """Simplified response that only returns the synthesis answer without raw data"""
    query: str = Field(..., description="Original query")
    answer: str = Field(..., description="Comprehensive answer with embedded citations")
    citations: List[CitationLink] = Field(
        default_factory=list,
        description="Structured citations with URLs for the UI",
    )
    confidence: str = Field(..., description="Confidence level (high|medium|low)")
    data_quality: str = Field(..., description="Assessment of data quality and completeness")
    processing_time: float = Field(..., description="Processing time in seconds")
    sources_used: List[str] = Field(default_factory=list, description="Sources used")

    @field_validator("citations", mode="before")
    @classmethod
    def _coerce_simple_citations(cls, v: Any) -> Any:
        from utils.citation_links import normalize_citation_entries

        return normalize_citation_entries(v)


class SoATableResult(BaseModel):
    """Schedule of Activities table extraction result"""
    nct_id: str = Field(..., description="NCT identifier")
    table_title: str = Field(..., description="Table title")
    page_number: int = Field(..., description="Page number in protocol")
    table_data: List[Dict[str, Any]] = Field(..., description="Extracted table data")
    extraction_method: str = Field(..., description="Method used for extraction")
    confidence_score: float = Field(..., description="Extraction confidence (0-1)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class TrialSummary(BaseModel):
    """Trial summary information for SoA data"""
    nct_id: str = Field(..., description="NCT identifier")
    title: str = Field(..., description="Trial title")
    condition: str = Field(..., description="Trial condition")
    phase: Optional[str] = Field(None, description="Trial phase")
    status: Optional[str] = Field(None, description="Trial status")
    sponsor: Optional[str] = Field(None, description="Trial sponsor")
    enrollment: Optional[int] = Field(None, description="Trial enrollment")
    soa_table_count: int = Field(..., description="Number of SoA tables extracted")

class SoADataModel(BaseModel):
    """Unified Schedule of Activities data model"""
    trial_summaries: List[TrialSummary] = Field(..., description="List of trial summaries")
    soa_table_details: List[SoATableResult] = Field(..., description="List of extracted SoA tables")
    hasSoAContent: bool = Field(..., description="Whether SoA content was found")
    soa_indicators: str = Field(..., description="Description of SoA extraction results")
    extraction_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional extraction metadata")

class ProtocolMetadata(BaseModel):
    """Protocol document metadata"""
    nct_id: str = Field(..., description="NCT identifier")
    protocol_url: str = Field(..., description="Protocol PDF URL")
    document_type: str = Field(..., description="Document type")
    has_protocol: bool = Field(..., description="Whether document contains protocol")
    download_path: Optional[str] = Field(None, description="Local download path")
    file_size: Optional[int] = Field(None, description="File size in bytes")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")

class SoAExtractionRequest(BaseModel):
    """Request for SoA extraction"""
    nct_id: str = Field(..., description="NCT identifier")
    force_redownload: bool = Field(default=False, description="Force re-download of protocol")
    extraction_methods: List[str] = Field(default=["graph"], description="Extraction methods to use")
    include_general_tables: bool = Field(default=False, description="Include non-SoA tables")

# New schemas for Claims and Payer Data Agents

class PatientResult(BaseModel):
    """Patient demographic and clinical data"""
    patient_id: str = Field(..., description="Patient identifier (hashed)")
    gender: str = Field(..., description="Patient gender")
    year_of_birth: int = Field(..., description="Year of birth")
    race: str = Field(..., description="Patient race")
    ethnicity: str = Field(..., description="Patient ethnicity")
    death_indicator: Optional[str] = Field(None, description="Death indicator")
    death_month: Optional[str] = Field(None, description="Death month if applicable")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class PrescriptionResult(BaseModel):
    """Prescription and medication data"""
    visit_id: str = Field(..., description="Visit identifier")
    patient_id: str = Field(..., description="Patient identifier")
    fill_date: str = Field(..., description="Prescription fill date")
    ndc: str = Field(..., description="National Drug Code")
    drug_name: str = Field(..., description="Drug name")
    days_supply: int = Field(..., description="Days supply")
    quantity: float = Field(..., description="Quantity dispensed")
    allowed_amount: float = Field(..., description="Allowed amount")
    copay_amount: float = Field(..., description="Copay amount")
    deductible_amount: float = Field(..., description="Deductible amount")
    paid_amount: float = Field(..., description="Paid amount")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class ProviderResult(BaseModel):
    """Healthcare provider data"""
    visit_id: str = Field(..., description="Visit identifier")
    service_id: str = Field(..., description="Service identifier")
    provider_npi: str = Field(..., description="Provider NPI (hashed)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class ClaimsResult(BaseModel):
    """General claims data result"""
    visit_id: str = Field(..., description="Visit identifier")
    patient_id: str = Field(..., description="Patient identifier")
    service_id: str = Field(..., description="Service identifier")
    date_start: str = Field(..., description="Service start date")
    date_end: str = Field(..., description="Service end date")
    diagnosis_code: Optional[str] = Field(None, description="Diagnosis code")
    procedure_code: Optional[str] = Field(None, description="Procedure code")
    allowed_amount: Optional[float] = Field(None, description="Allowed amount")
    paid_amount: Optional[float] = Field(None, description="Paid amount")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class ProductResult(BaseModel):
    """Pharmaceutical product data"""
    product_id: str = Field(..., description="Product identifier")
    brand_name: str = Field(..., description="Brand name")
    market_id: str = Field(..., description="Market identifier")
    competitor_flag: str = Field(..., description="Competitor flag")
    category: str = Field(..., description="Product category")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class SalesResult(BaseModel):
    """Sales and prescription data"""
    product_id: str = Field(..., description="Product identifier")
    new_rx_count: int = Field(..., description="New prescription count")
    refill_rx_count: int = Field(..., description="Refill prescription count")
    total_rx_count: int = Field(..., description="Total prescription count")
    wac_dollars: float = Field(..., description="WAC dollars")
    volume_units: int = Field(..., description="Volume units")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class PayerResult(BaseModel):
    """Payer and insurance data"""
    payer_plan_id: str = Field(..., description="Payer plan identifier")
    payer_plan_name: str = Field(..., description="Payer plan name")
    payer_id: str = Field(..., description="Payer identifier")
    plan_type: str = Field(..., description="Plan type")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class UtilizationResult(BaseModel):
    """Drug utilization analysis result"""
    drug_name: str = Field(..., description="Drug name")
    ndc: str = Field(..., description="National Drug Code")
    total_prescriptions: int = Field(..., description="Total prescriptions")
    average_days_supply: int = Field(..., description="Average days supply")
    average_quantity: float = Field(..., description="Average quantity")
    total_allowed_amount: float = Field(..., description="Total allowed amount")
    total_paid_amount: float = Field(..., description="Total paid amount")
    copay_amount: float = Field(..., description="Copay amount")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class CostAnalysisResult(BaseModel):
    """Cost analysis result"""
    dimension: str = Field(..., description="Analysis dimension (region, payer_type, procedure)")
    dimension_value: str = Field(..., description="Dimension value")
    average_allowed_amount: float = Field(..., description="Average allowed amount")
    average_paid_amount: float = Field(..., description="Average paid amount")
    total_providers: int = Field(..., description="Total providers")
    total_payers: int = Field(..., description="Total payers")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class AnalyticsResult(BaseModel):
    """General analytics result"""
    analysis_type: str = Field(..., description="Type of analysis")
    result_data: Dict[str, Any] = Field(..., description="Analysis results")
    confidence_score: float = Field(..., description="Confidence score (0-1)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class SiteResult(BaseModel):
    site_id: str = Field(..., description="Unique site identifier")
    site_name: str = Field(..., description="Site/organization name")
    site_type: Optional[str] = Field(None, description="Type of medical facility")
    address: Optional[str] = Field(None, description="Full address")
    city: Optional[str] = Field(None, description="City")
    state: Optional[str] = Field(None, description="State/Province")
    country: Optional[str] = Field(None, description="Country")
    postal_code: Optional[str] = Field(None, description="Postal/ZIP code")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    total_trials: Optional[int] = Field(None, description="Total number of trials")
    ongoing_trials: Optional[int] = Field(None, description="Number of ongoing trials")
    planned_trials: Optional[int] = Field(None, description="Number of planned trials")
    disease_areas: Optional[str] = Field(None, description="Disease areas covered")
    trial_ids: Optional[List[int]] = Field(default_factory=list, description="List of associated trial IDs")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional site metadata")

class TrialSiteResult(BaseModel):
    trial_id: int = Field(..., description="Trial identifier")
    site_count: int = Field(..., description="Number of sites for this trial")
    site_names: List[str] = Field(..., description="Names of participating sites")
    site_types: List[str] = Field(..., description="Types of participating sites")
    cities: List[str] = Field(..., description="Cities where sites are located")
    states: List[str] = Field(..., description="States where sites are located")
    countries: List[str] = Field(..., description="Countries where sites are located")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional trial-site metadata")

class GeographicResult(BaseModel):
    country: str = Field(..., description="Country name")
    state: Optional[str] = Field(None, description="State/Province name")
    site_count: int = Field(..., description="Number of sites in this region")
    total_trials: int = Field(..., description="Total trials in this region")
    ongoing_trials: int = Field(..., description="Ongoing trials in this region")
    planned_trials: int = Field(..., description="Planned trials in this region")
    avg_longitude: Optional[float] = Field(None, description="Average longitude")
    avg_latitude: Optional[float] = Field(None, description="Average latitude")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional geographic metadata")

# Simulation Agent Schemas
class SimulationRequest(BaseModel):
    """Request model for simulation operations"""
    query: str = Field(..., description="Simulation query")
    therapeutic_area: Optional[str] = Field(None, description="Therapeutic area")
    phase: Optional[str] = Field(None, description="Clinical trial phase")
    target_sample_size: Optional[int] = Field(None, description="Target sample size")
    enrollment_period_months: Optional[int] = Field(None, description="Enrollment period in months")
    number_of_countries: Optional[int] = Field(None, description="Number of countries")
    number_of_sites: Optional[int] = Field(None, description="Number of sites")
    conversation_history: List[Dict] = Field(default_factory=list, description="Conversation history")
    execution_mode: str = Field("dynamic", description="Execution mode")

class SimulationResponse(BaseModel):
    """Response model for simulation operations"""
    simulation_id: str = Field(..., description="Unique simulation identifier")
    query: str = Field(..., description="Original query")
    status: str = Field(..., description="Simulation status")
    execution_mode: str = Field(..., description="Execution mode used")
    results: Dict[str, Any] = Field(..., description="Simulation results")
    timestamp: str = Field(..., description="Timestamp of simulation")
    execution_time_seconds: float = Field(..., description="Execution time in seconds")

class RecruitmentCurve(BaseModel):
    """Recruitment curve data model"""
    months: List[int] = Field(..., description="Month numbers")
    cumulative_patients: List[int] = Field(..., description="Cumulative patient counts")
    confidence_intervals: Dict[str, List[int]] = Field(..., description="Confidence intervals")
    enrollment_rate: List[float] = Field(..., description="Enrollment rates per month")

# Site Map Agent Schemas
class SiteMapRequest(BaseModel):
    """Request model for site map generation"""
    query: str = Field(..., description="User query for site mapping")
    therapeutic_area: Optional[str] = Field(None, description="Therapeutic area")
    inclusion_criteria: List[str] = Field(default_factory=list, description="Inclusion criteria")
    exclusion_criteria: List[str] = Field(default_factory=list, description="Exclusion criteria")
    geographic_scope: Optional[Dict[str, Any]] = Field(None, description="Geographic scope")
    site_filters: Optional[Dict[str, Any]] = Field(None, description="Site filters")
    population_filters: Optional[Dict[str, Any]] = Field(None, description="Population filters")
    conversation_history: List[Dict] = Field(default_factory=list, description="Conversation history")

class SiteCandidate(BaseModel):
    """Candidate site for clinical trials"""
    site_id: str = Field(..., description="Unique site identifier")
    name: str = Field(..., description="Site name")
    address: str = Field(..., description="Site address")
    city: str = Field(..., description="City")
    state: str = Field(..., description="State")
    zip_code: str = Field(..., description="ZIP code")
    coordinates: Dict[str, float] = Field(..., description="Latitude and longitude")
    trial_experience: List[Dict[str, Any]] = Field(default_factory=list, description="Trial experience")
    population_density: float = Field(0.0, description="Population density")
    patient_pool_size: int = Field(0, description="Estimated patient pool size")
    inclusion_rate: float = Field(0.0, description="Inclusion rate")
    exclusion_rate: float = Field(0.0, description="Exclusion rate")
    site_score: float = Field(0.0, description="Overall site score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class ZipCodePopulation(BaseModel):
    """Population data for ZIP code"""
    zip_code: str = Field(..., description="ZIP code")
    population: int = Field(..., description="Total population")
    patient_count: int = Field(..., description="Patient count for therapeutic area")
    density: float = Field(..., description="Population density")
    coordinates: Optional[Dict[str, float]] = Field(None, description="Latitude and longitude coordinates")
    demographics: Dict[str, Any] = Field(default_factory=dict, description="Demographic breakdown")

class StatePopulation(BaseModel):
    """Population data for state"""
    state: str = Field(..., description="State name")
    population: int = Field(..., description="Total population")
    patient_count: int = Field(..., description="Patient count for therapeutic area")
    site_count: int = Field(..., description="Number of sites")
    avg_density: float = Field(..., description="Average population density")

class CountyPopulation(BaseModel):
    """Population data for county"""
    county: str = Field(..., description="County name")
    state: str = Field(..., description="State name")
    population: int = Field(..., description="Total population")
    patient_count: int = Field(..., description="Patient count for therapeutic area")
    facility_count: int = Field(0, description="Number of healthcare facilities")
    avg_density: float = Field(..., description="Average population density")

class PopulationOverlay(BaseModel):
    """Population overlay data for map"""
    zip_code_data: List[ZipCodePopulation] = Field(default_factory=list, description="ZIP code population data")
    state_data: List[StatePopulation] = Field(default_factory=list, description="State population data")
    county_data: List[CountyPopulation] = Field(default_factory=list, description="County population data")
    demographic_breakdown: Dict[str, Any] = Field(default_factory=dict, description="Overall demographic breakdown")

class SiteMapResponse(BaseModel):
    """Response model for site map generation"""
    map_id: str = Field(..., description="Unique map identifier")
    sites: List[SiteCandidate] = Field(..., description="Candidate sites")
    population_overlay: PopulationOverlay = Field(..., description="Population overlay data")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Applied filters")
    generated_at: str = Field(..., description="Generation timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata") 