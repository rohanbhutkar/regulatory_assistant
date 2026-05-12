"""
Dynamic Reasoning Engine for Clinical Research Assistant
Uses LLM to assess queries and construct custom execution graphs
"""
import asyncio
import json
import re
import uuid
from typing import Dict, List, Any, Optional, Tuple, TypedDict, Annotated
from datetime import datetime, timedelta
from collections import Counter
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from config import settings
from utils.logger import log_query, log_performance, log_error
from utils.cache import cache_manager
from agents.llm_agent import llm_agent
from agents.clinical_trials_agent import clinical_trials_agent
from agents.pubmed_agent import pubmed_agent
from agents.biomcp_agent import biomcp_agent
from agents.aact_agent import aact_agent
from agents.openfda_agent import OpenFDAAgent
from agents.fierce_pharma_agent import google_search_agent
from agents.simulation_agent import simulation_agent
from agents.trialtrove_agent import trialtrove_agent
from agents.fda_labels_agent import fda_labels_agent
from agents.site_trove_agent import site_trove_agent
from agents.site_map_agent import site_map_agent
from agents.goodrx_agent import goodrx_agent
from agents.ema_eu_agent import ema_eu_agent
from agents.china_regulatory_agent import china_regulatory_agent
from agents.nih_reporter_agent import nih_reporter_agent
from agents.npi_registry_agent import npi_registry_agent
from agents.openalex_agent import openalex_agent
from agents.crossref_agent import crossref_agent
from agents.ror_agent import ror_agent
from agents.open_payments_agent import open_payments_agent
from agents.eu_ctis_agent import eu_ctis_agent
from agents.isrctn_agent import isrctn_agent
from agents.cms_open_data_agent import cms_open_data_agent
from agents.fda_datadashboard_agent import fda_datadashboard_agent
from processing.data_processor import data_processor
from context_compression import maybe_compress_analysis_node_output
from graph.synthesis_map_reduce import map_reduce_meaningful_data
from graph.synthesis_prompt_constants import (
    CLINICAL_SYNTHESIS_SYSTEM_PROMPT,
    regulatory_comparison_user_hint,
)
from utils.citation_links import citation_link_from_content, dedupe_citation_links
from graph.truncation_utils import (
    calculate_dynamic_limits as _tu_calculate_dynamic_limits,
    emergency_truncation as _tu_emergency_truncation,
    estimate_data_tokens as _tu_estimate_data_tokens,
    estimate_tokens as _tu_estimate_tokens,
    progressive_truncation as _tu_progressive_truncation,
    truncate_section_to_tokens as _tu_truncate_section_to_tokens,
)
from utils.conversation_summarizer import (
    conversation_messages_to_dicts,
    maybe_summarize_conversation_messages,
)
from models.schemas import (
    DynamicQueryRequest, DynamicQueryResponse, GraphPlan, GraphNode, 
    Synthesis, Metadata, SimpleQueryResponse, ContextManager, ContextItem
)
from graph.planner_cached_document import build_graph_planner_cached_document
from graph.deep_research import (
    build_research_brief_and_outline,
    format_research_spec_for_planner,
    summarize_execution_for_verifier,
    verify_research_coverage,
    replan_new_nodes_json,
    replan_targeted_nodes_and_edges,
    merge_replan_into_plan,
    is_broad_query,
    broad_query_explanation,
    ui_brief_payload,
    ui_outline_payload,
    ui_verifier_payload,
    ui_replan_started_payload,
    node_result_ok_for_skip,
    build_compact_node_artifact,
)
from graph.deep_research_incremental import (
    reflect_on_step,
    refine_working_answer,
    reflect_and_refine_step_combined,
    truncate_for_reflection,
    should_apply_search_skip,
)
import logging

logger = logging.getLogger(__name__)

# Live HTTP API agents (no local site database); uniform `search(query, max_results)`.
LIVE_API_GRAPH_SOURCES = frozenset(
    {
        "nih_reporter",
        "npi_registry",
        "openalex",
        "crossref",
        "ror",
        "open_payments",
        "eu_ctis",
        "isrctn",
        "cms_open_data",
        "fda_datadashboard",
    }
)


def _query_suggests_ema_eu(query: str) -> bool:
    """Heuristic: user likely wants EMA / EU medicines JSON or ePI (for fallback planning)."""
    q = re.sub(r"\s+", " ", (query or "").lower()).strip()
    if not q:
        return False
    patterns = (
        r"\bema\b",
        r"\bepar\b",
        r"european medicines",
        r"european public assessment",
        r"\bdhpc\b",
        r"\bpsusa\b",
        r"\bprac\b",
        r"medicine shortage",
        r"orphan designation",
        r"centrali[sz]ed authori[sz]ation",
        r"post-?authori[sz]ation",
        r"paediatric investigation plan",
        r"pediatric investigation plan",
        r"referral procedure",
        r"\bepi\b.*\b(ema|eu|europe)\b",
        r"\bsmpc\b.*\b(eu|ema|europe)\b",
    )
    return any(re.search(p, q) for p in patterns)


def _format_regulatory_documents_for_query(
    regulatory_documents: List[Dict[str, Any]],
    max_total_chars: int = 48000,
) -> str:
    """Build a bounded text block from uploaded regulatory documents for LLM context."""
    parts: List[str] = []
    remaining = max_total_chars
    for doc in regulatory_documents:
        name = doc.get("filename") or doc.get("name") or "document"
        text = str(doc.get("extracted_text") or doc.get("text") or "")
        header = f"\n### {name}\n"
        budget = max(0, remaining - len(header) - 32)
        if budget <= 0:
            parts.append("\n...[additional document text omitted for size]")
            break
        excerpt = text[:budget]
        suffix = "\n…[truncated]" if len(text) > budget else ""
        chunk = f"{header}{excerpt}{suffix}"
        parts.append(chunk)
        remaining -= len(chunk)
    return "\n".join(parts)


def _langgraph_invoke_config(execution_order_len: int) -> dict:
    """LangGraph defaults recursion_limit to 25; long linear plans need a higher cap."""
    return {
        "recursion_limit": max(
            settings.GRAPH_RECURSION_LIMIT,
            execution_order_len + 24,
        )
    }


# Define the dynamic state schema
class DynamicGraphState(TypedDict):
    query: str
    graph_plan: Dict[str, Any]
    execution_results: Dict[str, Any]
    current_step: str
    execution_trace: List[Dict[str, Any]]
    error: str
    context_manager: ContextManager  # Enhanced context management


def _effective_web_regulatory_max_results(query: str, source: Optional[str], requested: object) -> int:
    """
    Avoid overly thin result sets for excerpt-heavy sources when the user question is regulatory
    or comparative (planner often emits small max_results).
    """
    try:
        base = int(requested) if requested is not None else 50
    except (TypeError, ValueError):
        base = 50
    cap = max(1, settings.MAX_RESULTS_PER_SOURCE)
    base = max(1, min(base, cap))
    if source not in ("google_search", "china_regulatory", "ema_eu"):
        return base
    ql = (query or "").lower()
    regulatory = any(
        t in ql
        for t in (
            "fda",
            "nmpa",
            "ema ",
            "ich",
            "regulatory",
            "regulator",
            "guidance",
            "guideline",
            "cde",
            "preclinical",
            "nonclinical",
            "non-clinical",
            "clinical trial application",
            "ind ",
            "ind-enabling",
            "submission",
            "pharmacovigilance",
        )
    )
    compare = any(
        t in ql
        for t in (
            "compare",
            "comparison",
            "versus",
            " vs ",
            " vs.",
            "contrast",
            "difference between",
            "differences between",
        )
    )
    if regulatory or compare:
        floor = min(28, cap)
        return max(base, floor)
    return base


_GOODRX_DRUG_SPLIT = re.compile(r",|\band\b|\bor\b", re.IGNORECASE)


def _split_goodrx_drug_names(raw: str) -> List[str]:
    """Tokenize GoodRx query into drug names (module-level regex avoids `import re` shadowing in node executors)."""
    s = (raw or "").strip()
    if not s:
        return []
    parts = [p.strip() for p in _GOODRX_DRUG_SPLIT.split(s) if p.strip()]
    return parts if parts else [s]


class DynamicReasoningEngine:
    def __init__(self):
        self.available_agents = {
            "clinical_trials": clinical_trials_agent,
            "pubmed": pubmed_agent,
            "biomcp": biomcp_agent,
            "aact": aact_agent,
            "openfda": OpenFDAAgent(),
            "google_search": google_search_agent,
            "trialtrove": trialtrove_agent,
            "fda_labels": fda_labels_agent,
            "simulation": simulation_agent,
            "site_trove": site_trove_agent,
            "site_map": site_map_agent,
            "llm": llm_agent,
            "goodrx": goodrx_agent,
            "ema_eu": ema_eu_agent,
            "china_regulatory": china_regulatory_agent,
            "nih_reporter": nih_reporter_agent,
            "npi_registry": npi_registry_agent,
            "openalex": openalex_agent,
            "crossref": crossref_agent,
            "ror": ror_agent,
            "open_payments": open_payments_agent,
            "eu_ctis": eu_ctis_agent,
            "isrctn": isrctn_agent,
            "cms_open_data": cms_open_data_agent,
            "fda_datadashboard": fda_datadashboard_agent,
            "claims_data": None,  # Will be initialized when needed
            "payer_data": None,   # Will be initialized when needed
            "healthcare_analytics": None,  # Will be initialized when needed
            "hitl_trial_selection": None  # Will be initialized when needed
        }
        
        # HITL Integration - DISABLED
        self.hitl_enabled = False
        self.trial_selection_manager = None  # Will be initialized when needed
    
    def _initialize_trial_selection_manager(self):
        """Initialize trial selection manager if not already done"""
        if self.trial_selection_manager is None:
            from processing.trial_data_processor import TrialSelectionManager
            self.trial_selection_manager = TrialSelectionManager()
    
    def _initialize_hitl_agent(self):
        """Initialize HITL agent if not already done"""
        if self.available_agents["hitl_trial_selection"] is None:
            from agents.hitl_agent import hitl_agent
            self.available_agents["hitl_trial_selection"] = hitl_agent
    
    def _should_pause_for_trial_selection(self, node: GraphNode, state: Dict[str, Any]) -> bool:
        """Determine if execution should pause for human trial selection - DISABLED"""
        # HITL is disabled, always return False
        return False
    
    async def _intercept_trial_selection(self, node_id: str, search_query: str, 
                                       trials: List[Any], source: str,
                                       context: Dict[str, Any], 
                                       progress_callback=None) -> Dict[str, Any]:
        """Intercept trial selection and initiate HITL process"""
        
        # Initialize trial selection manager if needed
        self._initialize_trial_selection_manager()
        
        # Generate execution ID
        import uuid
        execution_id = f"hitl_{uuid.uuid4().hex[:8]}"
        
        # Create selection state
        selection_state = await self.trial_selection_manager.create_selection_state(
            execution_id, search_query, trials, source, context
        )
        
        # Send pause notification to frontend via progress callback
        if progress_callback:
            pause_data = {
                "node_id": node_id,
                "node_type": "search",
                "status": "hitl_paused",
                "hitl_paused": True,
                "hitl_execution_id": execution_id,
                "hitl_pause_reason": "trial_selection",
                "suggestions": [s.model_dump() for s in selection_state.suggestions],
                "total_trials": selection_state.total_trials,
                "timeout_seconds": 300,
                "query": search_query
            }
            await progress_callback(pause_data)
        
        return {
            "status": "paused",
            "execution_id": execution_id,
            "selection_state": selection_state
        }
    
    async def assess_query_and_plan_graph(
        self,
        query: str,
        conversation_history: List[Dict] = None,
        study_context: Dict = None,
        selected_trials: List = None,
        selected_agents: List[str] = None,
        research_spec: Optional[Dict[str, Any]] = None,
        *,
        deep_plan: bool = False,
    ) -> GraphPlan:
        """Assess query and create a dynamic execution graph plan
        
        Args:
            query: The user's query
            conversation_history: Previous conversation context
            study_context: Study design context (phase, indication, drug name, etc.)
            selected_trials: List of selected reference trials
            selected_agents: Optional UI agent ids to bias source selection (empty = no constraint)
            research_spec: Optional brief + outline from deep-research pre-plan (injected into prompt).
            deep_plan: When True, use full GRAPH_PLAN_MAX_NODES budget and no strict search cap in the prompt.
                When False (default chat), planner is limited to compact node/search caps.
        """
        try:
            # Format conversation history for the prompt
            conversation_context = ""
            if conversation_history:
                conversation_context = "\n\nCONVERSATION HISTORY:\n"
                for i, message in enumerate(conversation_history):
                    # Handle both ConversationMessage objects and dictionaries
                    if hasattr(message, 'role'):
                        # Pydantic model
                        role = message.role
                        content = message.content
                    else:
                        # Dictionary
                        role = message.get("role", "unknown")
                        content = message.get("content", "")
                    conversation_context += f"{i+1}. {role.upper()}: {content}\n"
            
            # Format study context for the prompt
            study_context_str = ""
            if study_context:
                study_context_str = "\n\nSTUDY CONTEXT:\n"
                if study_context.get("phase"):
                    study_context_str += f"- Phase: {study_context['phase']}\n"
                if study_context.get("indication"):
                    study_context_str += f"- Indication: {study_context['indication']}\n"
                if study_context.get("drugName"):
                    study_context_str += f"- Drug: {study_context['drugName']}\n"
                if study_context.get("therapeuticArea"):
                    study_context_str += f"- Therapeutic Area: {study_context['therapeuticArea']}\n"
                if study_context.get("studyTitle"):
                    study_context_str += f"- Study Title: {study_context['studyTitle']}\n"
            
            # Format selected trials info
            trials_context_str = ""
            if selected_trials and len(selected_trials) > 0:
                trials_context_str = f"\n\nSELECTED REFERENCE TRIALS: {len(selected_trials)} trials available for context\n"
                # Add a few trial titles as examples
                for i, trial in enumerate(selected_trials[:3]):
                    if isinstance(trial, dict):
                        nct_id = trial.get('nctId') or trial.get('nct_id', 'Unknown')
                        title = trial.get('title', 'No title')
                        trials_context_str += f"- {nct_id}: {title}\n"
            
            agent_filter_str = ""
            if selected_agents:
                agent_filter_str = (
                    "\n\nUSER AGENT FOCUS (prefer these capabilities when compatible with the query; "
                    "if the query requires another source to answer, include the minimal additional node):\n- "
                    + "\n- ".join(selected_agents)
                    + "\nMap IDs to AVAILABLE SOURCES, e.g. clinical-trials → trialtrove or clinical_trials or aact; "
                    "fda-labels → fda_labels; openfda → openfda; ema-eu → ema_eu; cde-nmpa → china_regulatory; "
                    "google-search → google_search; pubmed → pubmed; "
                    "nih-grants → nih_reporter; npi-nppes → npi_registry; openalex → openalex; crossref → crossref; "
                    "ror → ror; open-payments → open_payments; eu-ctis → eu_ctis; isrctn → isrctn; "
                    "cms-data → cms_open_data; fda-dashboard → fda_datadashboard; good-rx → goodrx."
                )

            research_block = ""
            if research_spec:
                research_block = format_research_spec_for_planner(research_spec)
                research_block += """

When INTERNAL RESEARCH BRIEF is present above:
- Each search node MUST include in parameters: "outline_section_id" (string matching a section_id) and "facet" (one of: regulatory, clinical, commercial, sites, publications, meta).
- Add explicit "dependencies" between nodes when later searches should refine queries using earlier results (enables dynamic follow-up search strings).
"""

            _cap_n = int(settings.GRAPH_PLAN_MAX_NODES) if deep_plan else int(settings.GRAPH_PLAN_COMPACT_MAX_NODES)
            _cap_search = int(settings.GRAPH_PLAN_COMPACT_MAX_SEARCH_NODES)
            budget_prefix = ""
            if not deep_plan:
                budget_prefix = (
                    f"STRICT BUDGET (mandatory — do not violate):\n"
                    f"- At most {settings.GRAPH_PLAN_COMPACT_MAX_NODES} entries in the \"nodes\" array "
                    f"(including synthesize and any simulation or site_map nodes).\n"
                    f"- At most {_cap_search} nodes may have \"type\": \"search\".\n"
                    f"- Prefer one analyze node before synthesize unless two analyzes are essential within the budget.\n\n"
                )
            variable_planning_message = f"""{budget_prefix}You are an expert clinical research analyst. Analyze the following query and create an efficient execution plan.

QUERY: {query}{conversation_context}{study_context_str}{trials_context_str}{agent_filter_str}{research_block}

TASK: Create a JSON graph plan that efficiently answers the QUERY. Use the DOCUMENT (cached reference) for every source definition, rule, and the required JSON shape.

Return ONLY valid JSON without markdown formatting.
"""
            cached_doc = build_graph_planner_cached_document(max_nodes=_cap_n)
            response = await llm_agent.generate_structured_response_with_cached_document(
                variable_user_message=variable_planning_message,
                cached_document=cached_doc,
                max_tokens=settings.GRAPH_PLAN_MAX_TOKENS,
                use_document_cache=settings.ENABLE_GRAPH_PLANNER_PROMPT_CACHE,
            )
            
            # Parse the response (LLM may return an error string on rate limits / outages)
            rs = (response or "").strip()
            if rs.startswith("Error generating") or (rs and not rs.startswith("{")):
                raise ValueError(f"Planner returned non-JSON (likely LLM error): {rs[:400]}")

            try:
                plan_data = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    plan_data = json.loads(json_match.group())
                else:
                    raise ValueError("Could not parse graph plan JSON")
            
            # Validate required fields
            required_fields = ["reasoning", "nodes", "edges", "execution_order"]
            for field in required_fields:
                if field not in plan_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Convert to GraphPlan
            nodes = [
                GraphNode(
                    id=node["id"],
                    type=node["type"],
                    description=node["description"],
                    parameters=node.get("parameters", {}),
                    dependencies=node.get("dependencies", [])
                )
                for node in plan_data["nodes"]
            ]
            
            plan = GraphPlan(
                nodes=nodes,
                edges=plan_data["edges"],
                execution_order=plan_data["execution_order"],
                reasoning=plan_data["reasoning"],
            )
            return self._sanitize_dynamic_chat_plan(plan, deep_plan=deep_plan)
            
        except Exception as e:
            log_error(e, "Graph planning")
            print(f"❌ Graph planning failed: {e}")
            print(f"Response was: {response if 'response' in locals() else 'No response'}")
            print("Using fallback plan.")
            # Fallback to a simple plan
            return self._create_fallback_plan(query, deep_plan=deep_plan)
    
    def _create_fallback_plan(self, query: str, *, deep_plan: bool = True) -> GraphPlan:
        """Create a fallback plan when LLM planning fails"""
        if not deep_plan:
            base_nodes = [
                GraphNode(
                    id="search_trialtrove",
                    type="search",
                    description="Search TrialTrove for protocol-level trial context",
                    parameters={"source": "trialtrove", "max_results": 20},
                    dependencies=[],
                ),
                GraphNode(
                    id="search_pubmed",
                    type="search",
                    description="Search PubMed for publications",
                    parameters={"source": "pubmed", "max_results": 20},
                    dependencies=[],
                ),
            ]
            synth_deps = ["search_trialtrove", "search_pubmed"]
            edges = [
                {"from": "search_trialtrove", "to": "synthesize_results"},
                {"from": "search_pubmed", "to": "synthesize_results"},
            ]
            execution_order = ["search_trialtrove", "search_pubmed"]
            reasoning = "Compact fallback: TrialTrove + PubMed + synthesize."
            if _query_suggests_ema_eu(query):
                ema_focus = re.sub(r"\s+", " ", (query or "").strip())[:500] or "EMA EU medicines EPAR guidance shortages"
                base_nodes.insert(
                    0,
                    GraphNode(
                        id="search_ema_eu",
                        type="search",
                        description="EMA / EU medicines unified search",
                        parameters={
                            "source": "ema_eu",
                            "max_results": 25,
                            "search_focus": ema_focus,
                            "search_instructions": "Include product name, INN, and document-type keywords.",
                        },
                        dependencies=[],
                    ),
                )
                synth_deps.insert(0, "search_ema_eu")
                edges.insert(0, {"from": "search_ema_eu", "to": "synthesize_results"})
                execution_order.insert(0, "search_ema_eu")
                reasoning += " EMA/EU node added from query keywords."
            base_nodes.append(
                GraphNode(
                    id="synthesize_results",
                    type="synthesize",
                    description="Synthesize search results",
                    parameters={},
                    dependencies=synth_deps,
                )
            )
            execution_order.append("synthesize_results")
            plan = GraphPlan(
                nodes=base_nodes,
                edges=edges,
                execution_order=execution_order,
                reasoning=reasoning,
            )
            return self._sanitize_dynamic_chat_plan(plan, deep_plan=False)

        base_nodes = [
            GraphNode(
                id="search_trialtrove",
                type="search",
                description="Search TrialTrove database for biomarker data and protocol extracts",
                parameters={"source": "trialtrove", "max_results": 20},
                dependencies=[],
            ),
            GraphNode(
                id="search_pubmed",
                type="search",
                description="Search publications",
                parameters={"source": "pubmed", "max_results": 20},
                dependencies=[],
            ),
            GraphNode(
                id="search_openfda",
                type="search",
                description="Search FDA drug information",
                parameters={"source": "openfda", "max_results": 20},
                dependencies=[],
            ),
            GraphNode(
                id="search_google_clinical",
                type="search",
                description="Search for clinical trial information and research updates",
                parameters={
                    "source": "google_search",
                    "max_results": 15,
                    "search_focus": "clinical trials research updates",
                    "search_instructions": "focus on recent clinical trial results, Phase 3 studies, and research breakthroughs",
                },
                dependencies=[],
            ),
            GraphNode(
                id="search_google_industry",
                type="search",
                description="Search for industry news and market information",
                parameters={
                    "source": "google_search",
                    "max_results": 15,
                    "search_focus": "industry news market analysis",
                    "search_instructions": "include pharmaceutical industry news, market reports, company announcements, and regulatory updates",
                },
                dependencies=[],
            ),
        ]
        ema_focus = re.sub(r"\s+", " ", (query or "").strip())[:500] or "EMA EU medicines EPAR guidance shortages"
        synth_deps = [
            "search_trialtrove",
            "search_pubmed",
            "search_openfda",
            "search_google_clinical",
            "search_google_industry",
        ]
        edges = [
            {"from": "search_trialtrove", "to": "synthesize_results"},
            {"from": "search_pubmed", "to": "synthesize_results"},
            {"from": "search_openfda", "to": "synthesize_results"},
            {"from": "search_google_clinical", "to": "synthesize_results"},
            {"from": "search_google_industry", "to": "synthesize_results"},
        ]
        execution_order = [
            "search_trialtrove",
            "search_pubmed",
            "search_openfda",
            "search_google_clinical",
            "search_google_industry",
        ]
        reasoning_extra = ""
        if _query_suggests_ema_eu(query):
            base_nodes.insert(
                0,
                GraphNode(
                    id="search_ema_eu",
                    type="search",
                    description="EMA / EU medicines: bulk JSON (medicines, EPAR, post-auth, guidance, DHPC, PSUSA, PIP, orphan, shortages, referrals) and optional ePI FHIR",
                    parameters={
                        "source": "ema_eu",
                        "max_results": 25,
                        "search_focus": ema_focus,
                        "search_instructions": "Include product name, INN, ATC, procedure numbers, and document type (EPAR, shortage, DHPC, PSUSA, PIP, etc.) in the search string.",
                    },
                    dependencies=[],
                ),
            )
            synth_deps.insert(0, "search_ema_eu")
            edges.insert(0, {"from": "search_ema_eu", "to": "synthesize_results"})
            execution_order.insert(0, "search_ema_eu")
            reasoning_extra = " Includes EMA/EU (ema_eu) because the query matches EU regulatory keywords."

        base_nodes.append(
            GraphNode(
                id="synthesize_results",
                type="synthesize",
                description="Synthesize all results",
                parameters={},
                dependencies=synth_deps,
            )
        )
        execution_order.append("synthesize_results")
        plan = GraphPlan(
            nodes=base_nodes,
            edges=edges,
            execution_order=execution_order,
            reasoning=(
                "Fallback plan: TrialTrove, PubMed, OpenFDA, and Google (clinical + industry)."
                + reasoning_extra
            ),
        )
        return self._sanitize_dynamic_chat_plan(plan, deep_plan=True)

    def _sanitize_dynamic_chat_plan(self, plan: GraphPlan, *, deep_plan: bool = False) -> GraphPlan:
        """Strip protocol drafting and SoA-specific search sources from dynamic chat plans."""
        forbidden_node_types = frozenset({"protocol_generate", "protocol_full"})
        removed_ids = {n.id for n in plan.nodes if n.type in forbidden_node_types}
        source_swaps = {
            "aact_soa": "aact",
            "protocol_authoring": "trialtrove",
            "soa_extractor": "trialtrove",
        }
        swapped_search_source = False
        new_nodes: List[GraphNode] = []
        for n in plan.nodes:
            if n.type in forbidden_node_types:
                continue
            params = dict(n.parameters) if n.parameters else {}
            if n.type == "search":
                src = params.get("source")
                if isinstance(src, str) and src in source_swaps:
                    params["source"] = source_swaps[src]
                    swapped_search_source = True
            deps = [d for d in (n.dependencies or []) if d not in removed_ids]
            new_nodes.append(
                GraphNode(
                    id=n.id,
                    type=n.type,
                    description=n.description,
                    parameters=params,
                    dependencies=deps,
                )
            )
        search_ids = [n.id for n in new_nodes if n.type == "search"]
        fixed: List[GraphNode] = []
        for n in new_nodes:
            if n.type == "synthesize" and not n.dependencies and search_ids:
                fixed.append(
                    GraphNode(
                        id=n.id,
                        type=n.type,
                        description=n.description,
                        parameters=n.parameters,
                        dependencies=search_ids[: min(12, len(search_ids))],
                    )
                )
            else:
                fixed.append(n)
        new_nodes = fixed
        new_order = [nid for nid in plan.execution_order if nid not in removed_ids]
        new_edges = [
            e
            for e in plan.edges
            if e.get("from") not in removed_ids and e.get("to") not in removed_ids
        ]
        note = ""
        if removed_ids or swapped_search_source:
            note = (
                " [Dynamic chat: protocol drafting nodes removed; aact_soa/protocol_authoring/soa_extractor "
                "search sources mapped to aact or trialtrove.]"
            )

        if not deep_plan:
            ms = max(1, int(getattr(settings, "GRAPH_PLAN_COMPACT_MAX_SEARCH_NODES", 3) or 3))
            by_id_pre = {n.id: n for n in new_nodes}
            search_ids_ordered = [
                nid for nid in new_order if nid in by_id_pre and by_id_pre[nid].type == "search"
            ]
            drop_searches = set(search_ids_ordered[ms:])
            if drop_searches:
                new_nodes = [n for n in new_nodes if n.id not in drop_searches]
                new_order = [nid for nid in new_order if nid not in drop_searches]
                new_edges = [
                    e
                    for e in new_edges
                    if e.get("from") not in drop_searches and e.get("to") not in drop_searches
                ]
                note += f" [Compact plan: kept first {ms} search node(s); dropped {len(drop_searches)} extra search(es).]"

        _MAX_PLAN_NODES = int(settings.GRAPH_PLAN_MAX_NODES) if deep_plan else int(
            settings.GRAPH_PLAN_COMPACT_MAX_NODES
        )
        if len(new_nodes) > _MAX_PLAN_NODES:
            by_id = {n.id: n for n in new_nodes}
            synth_nodes = [n for n in new_nodes if n.type == "synthesize"]
            ordered_ns_ids: List[str] = []
            seen_ns: set[str] = set()
            for oid in new_order:
                n = by_id.get(oid)
                if n and n.type != "synthesize" and oid not in seen_ns:
                    ordered_ns_ids.append(oid)
                    seen_ns.add(oid)
            for n in new_nodes:
                if n.type != "synthesize" and n.id not in seen_ns:
                    ordered_ns_ids.append(n.id)
                    seen_ns.add(n.id)
            room = max(0, _MAX_PLAN_NODES - len(synth_nodes))
            kept_non_synth_ids = ordered_ns_ids[:room]
            kept_ids = set(kept_non_synth_ids) | {n.id for n in synth_nodes}
            capped_nodes: List[GraphNode] = []
            for nid in kept_non_synth_ids:
                if nid in by_id:
                    capped_nodes.append(by_id[nid])
            capped_nodes.extend(synth_nodes)
            capped_nodes = [
                GraphNode(
                    id=n.id,
                    type=n.type,
                    description=n.description,
                    parameters=dict(n.parameters) if n.parameters else {},
                    dependencies=[d for d in (n.dependencies or []) if d in kept_ids],
                )
                for n in capped_nodes
            ]
            search_ids_c = [n.id for n in capped_nodes if n.type == "search"]
            capped_fixed: List[GraphNode] = []
            for n in capped_nodes:
                if n.type == "synthesize" and (not n.dependencies) and search_ids_c:
                    capped_fixed.append(
                        GraphNode(
                            id=n.id,
                            type=n.type,
                            description=n.description,
                            parameters=n.parameters,
                            dependencies=search_ids_c[: min(12, len(search_ids_c))],
                        )
                    )
                else:
                    capped_fixed.append(n)
            new_nodes = capped_fixed
            new_order = [nid for nid in new_order if nid in kept_ids]
            for nid in kept_ids:
                if nid not in new_order:
                    new_order.append(nid)
            new_edges = [
                e for e in new_edges if e.get("from") in kept_ids and e.get("to") in kept_ids
            ]
            cap_label = "full" if deep_plan else "compact"
            note += f" [Dynamic chat: execution plan capped to {_MAX_PLAN_NODES} nodes ({cap_label} budget).]"

        return GraphPlan(
            nodes=new_nodes,
            edges=new_edges,
            execution_order=new_order,
            reasoning=(plan.reasoning or "") + note,
        )

    def _record_node_artifact(self, new_state: Dict[str, Any], node: GraphNode) -> None:
        cm = new_state.get("context_manager")
        if cm is None:
            return
        payload = new_state.get("execution_results", {}).get(node.id)
        if payload is None:
            return
        art = build_compact_node_artifact(node, payload)
        params = node.parameters or {}
        cm.add_context_item(
            layer_type="node_artifact",
            content=art,
            source="node_artifact",
            node_id=node.id,
            metadata={
                "facet": params.get("facet"),
                "outline_section_id": params.get("outline_section_id"),
            },
        )

    def _merge_context_manager_from(self, target: ContextManager, source: ContextManager, tag: str) -> None:
        for layer in source.layers:
            for item in layer.items:
                target.add_context_item(
                    layer_type=layer.layer_type,
                    content=item.content,
                    source=f"{item.source}_{tag}",
                    node_id=(item.node_id or "") + f"_{tag}" if item.node_id else None,
                    metadata={**(item.metadata or {}), "parallel_subrun": tag},
                )

    async def _seed_context_manager(
        self,
        context_manager: ContextManager,
        effective_query: str,
        conversation_history: List[Dict] = None,
        study_context: Dict = None,
        selected_trials: List = None,
        research_spec: Optional[Dict[str, Any]] = None,
        run_id: Optional[str] = None,
    ) -> None:
        if conversation_history:
            conv_dicts = conversation_messages_to_dicts(conversation_history)
            conv_dicts = await maybe_summarize_conversation_messages(conv_dicts)
            for message in conv_dicts:
                role = message.get("role", "unknown")
                content = message.get("content", "")
                timestamp = message.get("timestamp", 0)
                meta = {k: v for k, v in message.items() if k not in ("role", "content", "timestamp")}
                context_manager.add_context_item(
                    layer_type="conversation",
                    content={"role": role, "content": content},
                    source="conversation_history",
                    node_id="conversation",
                    metadata={"timestamp": timestamp, **meta},
                )
        if study_context:
            context_manager.add_context_item(
                layer_type="study_design",
                content=study_context,
                source="study_designer_ui",
                node_id="study_context",
                metadata={"type": "study_parameters"},
            )
        if selected_trials:
            context_manager.add_context_item(
                layer_type="trial_data",
                content={"trials": selected_trials, "count": len(selected_trials)},
                source="selected_reference_trials",
                node_id="selected_trials",
                metadata={"type": "reference_trials", "trial_count": len(selected_trials)},
            )
        if research_spec:
            context_manager.add_context_item(
                layer_type="research_spec",
                content=research_spec,
                source="deep_research",
                node_id="research_spec",
                metadata={"run_id": run_id} if run_id else {},
            )

    async def _deep_research_after_evidence_step(
        self,
        incremental_dr: Dict[str, Any],
        new_state: DynamicGraphState,
        node: GraphNode,
        plan: GraphPlan,
        progress_callback,
    ) -> None:
        """Assess each evidence step, refine running draft, optionally skip later searches."""
        cm = new_state.get("context_manager")
        if not cm:
            return
        gc = cm.global_context
        spec = incremental_dr.get("research_spec") or {}
        payload = new_state["execution_results"].get(node.id)
        preview = truncate_for_reflection(payload)
        try:
            idx = plan.execution_order.index(node.id)
        except ValueError:
            idx = -1
        upcoming_desc: List[str] = []
        for uid in plan.execution_order[idx + 1 : idx + 8]:
            un = next((n for n in plan.nodes if n.id == uid), None)
            if un:
                upcoming_desc.append(f"{uid} ({un.type}): {(un.description or '')[:140]}")

        source = None
        if node.type == "search" and isinstance(node.parameters, dict):
            source = str(node.parameters.get("source") or "")

        prev_draft = str(gc.get("deep_research_working_answer") or "")
        if settings.DEEP_RESEARCH_INCREMENTAL_COMBINED_LLM:
            reflection, draft = await reflect_and_refine_step_combined(
                new_state["query"],
                spec,
                node.id,
                node.type,
                source,
                preview,
                upcoming_desc,
                prev_draft,
            )
        else:
            reflection = await reflect_on_step(
                new_state["query"],
                spec,
                node.id,
                node.type,
                source,
                preview,
                upcoming_desc,
            )
            draft = await refine_working_answer(
                new_state["query"],
                spec,
                prev_draft,
                node.id,
                reflection,
                preview,
            )

        reflections = gc.setdefault("deep_research_reflections", [])
        reflections.append(
            {
                "node_id": node.id,
                "node_type": node.type,
                "source": source,
                **{
                    k: v
                    for k, v in reflection.items()
                    if k not in ("node_id", "node_type", "source")
                },
            }
        )
        if draft:
            gc["deep_research_working_answer"] = draft

        if should_apply_search_skip(reflection):
            gc["deep_research_skip_searches"] = True
            gc["deep_research_skip_reason"] = reflection.get("rationale") or "Low marginal value for further searches."

        emit = incremental_dr.get("emit")
        if callable(emit):
            thinking = [
                f"Assessed step `{node.id}` ({node.type}): usefulness {reflection.get('usefulness_score')}, quality {reflection.get('source_quality')}.",
                reflection.get("rationale") or "",
            ]
            if reflection.get("what_changed"):
                thinking.append(f"Folded into draft: {reflection.get('what_changed')}")
            await emit(
                "deep_research_phase",
                "incremental",
                {
                    "message": f"Incremental reflection after {node.id}",
                    "thinking_lines": [t for t in thinking if t],
                    "node_id": node.id,
                    "reflection": reflection,
                    "working_answer_excerpt": (draft or prev_draft)[:1200],
                    "skip_remaining_searches": bool(gc.get("deep_research_skip_searches")),
                },
            )

    async def _run_graph_to_final_state(
        self,
        graph_plan: GraphPlan,
        effective_query: str,
        context_manager: ContextManager,
        progress_callback,
        seed_execution_results: Optional[Dict[str, Any]] = None,
        incremental_dr: Optional[Dict[str, Any]] = None,
        *,
        sanitize_deep_plan: bool = False,
    ) -> DynamicGraphState:
        graph_plan = self._sanitize_dynamic_chat_plan(graph_plan, deep_plan=sanitize_deep_plan)
        dynamic_graph = self._create_dynamic_graph(
            graph_plan, progress_callback, incremental_dr=incremental_dr
        )
        initial_state = DynamicGraphState(
            query=effective_query,
            graph_plan=graph_plan.dict(),
            execution_results=dict(seed_execution_results or {}),
            current_step="",
            execution_trace=[],
            error="",
            context_manager=context_manager,
        )
        final_state = await dynamic_graph.ainvoke(
            initial_state,
            config=_langgraph_invoke_config(len(graph_plan.execution_order)),
        )
        return final_state

    @staticmethod
    def _split_outline_into_chunks(
        outline: List[Dict[str, Any]], n: int
    ) -> List[List[Dict[str, Any]]]:
        """Split outline into n non-empty contiguous chunks (for parallel sub-runs)."""
        if not outline or n < 2:
            return []
        n = min(n, len(outline))
        chunks: List[List[Dict[str, Any]]] = []
        base, rem = divmod(len(outline), n)
        idx = 0
        for i in range(n):
            sz = base + (1 if i < rem else 0)
            if sz <= 0:
                break
            chunks.append(outline[idx : idx + sz])
            idx += sz
        return [c for c in chunks if c]

    @staticmethod
    def _partition_graph_plan_for_outline_sections(
        plan: GraphPlan,
        outline_chunk: List[Dict[str, Any]],
    ) -> Optional[GraphPlan]:
        """
        Subgraph for parallel prefetch: searches tagged with outline_section_id in this chunk,
        plus non-synthesize nodes whose dependencies are satisfied within the subset (no second planner LLM).
        """
        section_ids = {
            str(s.get("section_id") or "").strip()
            for s in outline_chunk
            if isinstance(s, dict) and str(s.get("section_id") or "").strip()
        }
        if not section_ids:
            return None
        nodes_by_id = {n.id: n for n in plan.nodes}
        synth_ids = {n.id for n in plan.nodes if n.type == "synthesize"}

        seed = {
            n.id
            for n in plan.nodes
            if n.type == "search"
            and str(n.parameters.get("outline_section_id") or "").strip() in section_ids
        }
        if not seed:
            return None

        kept: set[str] = set(seed)
        changed = True
        while changed:
            changed = False
            for n in plan.nodes:
                if n.id in kept or n.type == "synthesize":
                    continue
                deps = list(n.dependencies or [])
                if not deps:
                    continue
                if all(d in kept for d in deps):
                    kept.add(n.id)
                    changed = True

        kept -= synth_ids
        if not kept:
            return None

        order = [nid for nid in plan.execution_order if nid in kept]
        for nid in kept:
            if nid not in order:
                order.append(nid)

        kept_nodes = [nodes_by_id[nid] for nid in order if nid in nodes_by_id]
        kept_ids = set(order)
        edges = [
            e for e in plan.edges if e.get("from") in kept_ids and e.get("to") in kept_ids
        ]
        sid_preview = ",".join(sorted(section_ids)[:4])
        more = "…" if len(section_ids) > 4 else ""
        return GraphPlan(
            nodes=kept_nodes,
            edges=edges,
            execution_order=order,
            reasoning=(plan.reasoning or "")
            + f" [Parallel prefetch: outline {sid_preview}{more}]",
        )

    def _create_dynamic_graph(
        self,
        plan: GraphPlan,
        progress_callback=None,
        incremental_dr: Optional[Dict[str, Any]] = None,
    ):
        """Create a LangGraph from the plan"""
        
        def create_node_function(node: GraphNode):
            """Create a function for a specific node"""
            
            async def node_function(state: DynamicGraphState) -> DynamicGraphState:
                try:
                    prior_result = state.get("execution_results", {}).get(node.id)
                    if prior_result is not None and node_result_ok_for_skip(prior_result):
                        new_state = dict(state)
                        new_state["current_step"] = node.id
                        if progress_callback:
                            try:
                                await progress_callback({
                                    "node_id": node.id,
                                    "node_type": node.type,
                                    "status": "skipped",
                                    "start_time": datetime.now().isoformat(),
                                    "end_time": datetime.now().isoformat(),
                                    "description": node.description,
                                    "error": "",
                                })
                            except Exception:
                                pass
                        return new_state

                    # Create a new state to avoid concurrent updates
                    new_state = dict(state)
                    new_state["current_step"] = node.id
                    new_state["execution_trace"].append({
                        "node_id": node.id,
                        "node_type": node.type,
                        "status": "started",
                        "start_time": datetime.now().isoformat(),
                        "description": node.description
                    })
                    
                    # Send start progress callback if provided
                    if progress_callback:
                        print(f"🔔 Starting node: {node.id}")
                        start_progress_data = {
                            "node_id": node.id,
                            "node_type": node.type,
                            "status": "started",
                            "start_time": new_state["execution_trace"][-1]["start_time"],
                            "end_time": None,
                            "description": node.description,
                            "error": ""
                        }
                        try:
                            await progress_callback(start_progress_data)
                            print(f"✅ Start progress callback completed for node: {node.id}")
                        except Exception as e:
                            print(f"⚠️ Error calling start progress callback: {e}")
                    else:
                        print(f"⚠️ No progress callback provided for node: {node.id}")
                    
                    # Execute based on node type
                    if node.type == "search":
                        source = node.parameters.get("source")
                        max_results = node.parameters.get("max_results", 50)
                        max_results = _effective_web_regulatory_max_results(
                            new_state.get("query", ""), source, max_results
                        )
                        search_focus = node.parameters.get("search_focus", "")
                        
                        # DYNAMIC QUERY CONSTRUCTION: Build search query based on previous node results
                        search_query = await self._build_dynamic_search_query(
                            node, 
                            new_state, 
                            plan, 
                            search_focus
                        )
                        
                        print(f"🔍 Dynamic search query for {node.id}: {search_query}")

                        dr_search_skipped = False
                        if incremental_dr and incremental_dr.get("enabled") and new_state.get("context_manager"):
                            gc0 = new_state["context_manager"].global_context
                            if gc0.get("deep_research_skip_searches"):
                                new_state["execution_results"][node.id] = [
                                    {
                                        "deep_research_skipped": True,
                                        "reason": str(
                                            gc0.get("deep_research_skip_reason")
                                            or "Earlier reflection judged remaining searches as low marginal value."
                                        ),
                                    }
                                ]
                                dr_search_skipped = True

                        if dr_search_skipped:
                            pass
                        elif source in self.available_agents:
                            agent = self.available_agents[source]
                            results = []
                            
                            if source == "clinical_trials":
                                results = await agent.search_studies(search_query, max_results=max_results)
                                new_state["execution_results"][node.id] = [r.dict() for r in results]
                            elif source == "pubmed":
                                results = await agent.search_publications(search_query, max_results=max_results)
                                new_state["execution_results"][node.id] = [r.dict() for r in results]
                            elif source == "biomcp":
                                results = await agent.search_data(search_query, max_results=max_results)
                                new_state["execution_results"][node.id] = [r.dict() for r in results]
                            elif source == "aact":
                                results = await agent.search_studies(
                                    search_query,
                                    max_results=max_results,
                                    node_description=node.description,
                                    node_parameters=node.parameters
                                )
                                new_state["execution_results"][node.id] = [r.dict() for r in results]
                                
                                # CRITICAL FIX: Add raw trial data to context manager
                                # This ensures the LLM can access actual trial records, not just summaries
                                if new_state.get("context_manager") and results:
                                    print(f"📋 Adding {len(results)} AACT trials to context manager")
                                    for trial in results:
                                        # Convert to dict if it's a Pydantic model
                                        trial_dict = trial.dict() if hasattr(trial, 'dict') else trial
                                        new_state["context_manager"].add_context_item(
                                            layer_type="search",
                                            content=trial_dict,
                                            source="aact",
                                            node_id=node.id,
                                            metadata={
                                                "trial_count": len(results),
                                                "search_query": search_query,
                                                "nct_id": trial_dict.get('nct_id', 'Unknown'),
                                                "phase": trial_dict.get('phase', 'Unknown'),
                                                "condition": trial_dict.get('condition', 'Unknown')
                                            }
                                        )
                            elif source == "openfda":
                                results = await agent.search_drugs(search_query, max_results=max_results)
                                new_state["execution_results"][node.id] = [r.dict() for r in results]
                            elif source == "ema_eu":
                                results = await agent.search(search_query, max_results=max_results)
                                new_state["execution_results"][node.id] = [r.dict() for r in results]
                            elif source == "google_search":
                                # Get search instructions from node parameters
                                search_instructions = node.parameters.get("search_instructions", "")
                                results = await agent.search_web(search_query, search_instructions, max_results=max_results)
                                new_state["execution_results"][node.id] = [r.dict() for r in results]
                            elif source == "china_regulatory":
                                search_instructions = node.parameters.get("search_instructions", "")
                                results = await agent.search_regulatory(
                                    search_query, search_instructions, max_results=max_results
                                )
                                new_state["execution_results"][node.id] = [r.dict() for r in results]
                            elif source == "trialtrove":
                                results = await agent.search_studies(search_query, max_results=max_results)
                                # Store TrialTrove results as objects, not dictionaries, for protocol generation compatibility
                                new_state["execution_results"][node.id] = results
                                
                                # CRITICAL FIX: Add raw trial data to context manager
                                # This ensures the LLM can access actual trial records, not just summaries
                                if new_state.get("context_manager") and results:
                                    print(f"📋 Adding {len(results)} TrialTrove trials to context manager")
                                    for trial in results:
                                        # Convert to dict if it's a Pydantic model
                                        trial_dict = trial.dict() if hasattr(trial, 'dict') else trial
                                        new_state["context_manager"].add_context_item(
                                            layer_type="search",
                                            content=trial_dict,
                                            source="trialtrove",
                                            node_id=node.id,
                                            metadata={
                                                "trial_count": len(results),
                                                "search_query": search_query,
                                                "nct_id": trial_dict.get('nct_id', 'Unknown'),
                                                "phase": trial_dict.get('phase', 'Unknown'),
                                                "condition": trial_dict.get('condition', 'Unknown')
                                            }
                                        )
                            elif source == "fda_labels":
                                results = await agent.search_labels(search_query, max_results=max_results)
                                new_state["execution_results"][node.id] = results
                                # FDA labels results are already dictionaries, no need to call .dict()
                            elif source == "goodrx":
                                raw = (search_query or "").strip()
                                if not raw:
                                    results = []
                                    new_state["execution_results"][node.id] = []
                                else:
                                    drug_names = _split_goodrx_drug_names(raw)
                                    drug_limit = max(1, min(max_results, 10))
                                    drug_names = drug_names[:drug_limit]
                                    results = await agent.search_drugs(drug_names)
                                    new_state["execution_results"][node.id] = [
                                        r.dict() for r in results
                                    ]
                            elif source == "claims_data":
                                # Initialize claims data agent if not already done
                                if self.available_agents[source] is None:
                                    from agents.claims_data_agent import claims_data_agent
                                    self.available_agents[source] = claims_data_agent
                                
                                agent = self.available_agents[source]
                                # Determine which claims search method to use based on query
                                if any(term in search_query.lower() for term in ['patient', 'demographic', 'age', 'gender', 'race']):
                                    results = await agent.search_patients(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['prescription', 'drug', 'medication', 'cost', 'price']):
                                    results = await agent.search_prescriptions(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['diagnosis', 'condition', 'disease', 'icd']):
                                    results = await agent.search_diagnoses(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['cost', 'procedure', 'cpt', 'region']):
                                    results = await agent.get_cost_analysis(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['enrollment', 'payer', 'insurance', 'benefit']):
                                    results = await agent.get_enrollment_analysis(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['icd', 'diagnosis code', 'diagnosis codes']):
                                    results = await agent.analyze_icd_codes(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['hcpcs', 'hcpcs code', 'hcpcs codes']):
                                    results = await agent.analyze_hcpcs_codes(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['cpt', 'cpt code', 'cpt codes']):
                                    results = await agent.analyze_cpt_codes(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['comprehensive', 'detailed', 'analysis']):
                                    results = await agent.search_diagnoses(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['cost pattern', 'cost patterns', 'cost analysis']):
                                    group_by = 'diagnosis' if 'diagnosis' in search_query.lower() else 'procedure'
                                    results = await agent.analyze_cost_patterns(search_query, group_by=group_by, max_results=max_results)
                                else:
                                    # Default to prescription search
                                    results = await agent.search_prescriptions(search_query, max_results=max_results)
                                
                                new_state["execution_results"][node.id] = results
                            elif source == "payer_data":
                                # Initialize payer data agent if not already done
                                if self.available_agents[source] is None:
                                    from agents.payer_data_agent import payer_data_agent
                                    self.available_agents[source] = payer_data_agent
                                
                                agent = self.available_agents[source]
                                # Determine which payer search method to use based on query
                                if any(term in search_query.lower() for term in ['sales trend', 'sales trends', 'trend analysis']):
                                    results = await agent.analyze_sales_trends(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['market penetration', 'penetration', 'market share']):
                                    results = await agent.analyze_market_penetration(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['rebate', 'rebates', 'payer rebate']):
                                    results = await agent.analyze_payer_rebates(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['formulary', 'coverage', 'tier']):
                                    results = await agent.analyze_formulary_coverage(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['competitive', 'competition', 'landscape']):
                                    results = await agent.analyze_competitive_landscape(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['customer', 'segment', 'purchasing']):
                                    results = await agent.analyze_customer_segments(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['product', 'drug', 'brand', 'therapeutic']):
                                    results = await agent.search_products(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['sales', 'prescription', 'volume', 'revenue']):
                                    results = await agent.search_sales_data(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['payer', 'plan', 'insurance']):
                                    results = await agent.search_payer_plans(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['market', 'analysis']):
                                    results = await agent.get_market_analysis(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['competitive', 'competitor']):
                                    results = await agent.get_competitive_analysis(search_query, max_results=max_results)
                                else:
                                    # Default to product search
                                    results = await agent.search_products(search_query, max_results=max_results)
                                
                                new_state["execution_results"][node.id] = results
                            elif source == "healthcare_analytics":
                                # Initialize healthcare analytics agent if not already done
                                if self.available_agents[source] is None:
                                    from agents.healthcare_analytics_agent import healthcare_analytics_agent
                                    self.available_agents[source] = healthcare_analytics_agent
                                
                                agent = self.available_agents[source]
                                # Determine which analytics method to use based on query
                                if any(term in search_query.lower() for term in ['utilization', 'drug', 'prescription']):
                                    results = await agent.analyze_drug_utilization(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['cost', 'trend', 'region', 'payer']):
                                    results = await agent.analyze_cost_trends(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['patient', 'demographic', 'population', 'condition']):
                                    results = await agent.analyze_patient_populations(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['market', 'opportunity', 'competitive']):
                                    results = await agent.analyze_market_opportunities(search_query, max_results=max_results)
                                else:
                                    # Default to utilization analysis
                                    results = await agent.analyze_drug_utilization(search_query, max_results=max_results)
                                
                                new_state["execution_results"][node.id] = results
                            elif source == "hitl_trial_selection":
                                # Initialize HITL agent if not already done
                                self._initialize_hitl_agent()
                                
                                agent = self.available_agents[source]
                                
                                # Prepare context for HITL agent
                                context = {
                                    "execution_results": new_state["execution_results"],
                                    "query": new_state["query"],
                                    "graph_plan": new_state["graph_plan"]
                                }
                                
                                # Process HITL request
                                hitl_result = await agent.process_request(
                                    search_query, context, max_results=max_results
                                )
                                
                                # Store HITL result
                                new_state["execution_results"][node.id] = hitl_result
                                
                                # Send progress update
                                if progress_callback:
                                    progress_data = {
                                        "node_id": node.id,
                                        "node_type": node.type,
                                        "status": "completed",
                                        "hitl_result": hitl_result,
                                        "execution_id": hitl_result.get("execution_id"),
                                        "selected_trials": hitl_result.get("selected_trials", []),
                                        "total_trials": hitl_result.get("total_trials", 0)
                                    }
                                    await progress_callback(progress_data)
                            elif source == "site_trove":
                                agent = self.available_agents[source]
                                # Determine which site method to use based on query
                                if any(term in search_query.lower() for term in ['details', 'specific', 'about', 'information']):
                                    # Extract site name from query for specific site details
                                    import re
                                    # Look for patterns like "details about X", "information on X", "tell me about X"
                                    site_patterns = [
                                        r'details about (.+)',
                                        r'information on (.+)',
                                        r'tell me about (.+)',
                                        r'about (.+)',
                                        r'details for (.+)',
                                        r'characteristics of (.+)'
                                    ]
                                    site_name = None
                                    for pattern in site_patterns:
                                        match = re.search(pattern, search_query, re.IGNORECASE)
                                        if match:
                                            site_name = match.group(1).strip()
                                            break
                                    
                                    if site_name:
                                        results = await agent.get_site_details(site_name)
                                        if results:
                                            results = [results]  # Convert single result to list
                                        else:
                                            results = []
                                    else:
                                        # Fallback to site search
                                        results = await agent.search_sites(search_query, max_results=max_results)
                                        
                                elif any(term in search_query.lower() for term in ['compare', 'comparison', 'vs', 'versus']):
                                    # Extract site names for comparison
                                    import re
                                    # Look for patterns like "compare X and Y", "X vs Y", "X versus Y"
                                    compare_patterns = [
                                        r'compare (.+) and (.+)',
                                        r'(.+) vs (.+)',
                                        r'(.+) versus (.+)',
                                        r'comparison between (.+) and (.+)'
                                    ]
                                    site_names = []
                                    for pattern in compare_patterns:
                                        match = re.search(pattern, search_query, re.IGNORECASE)
                                        if match:
                                            site_names = [match.group(1).strip(), match.group(2).strip()]
                                            break
                                    
                                    if len(site_names) >= 2:
                                        results = await agent.compare_sites(site_names)
                                        if results and 'error' not in results:
                                            results = [results]  # Convert single result to list
                                        else:
                                            results = []
                                    else:
                                        # Fallback to site search
                                        results = await agent.search_sites(search_query, max_results=max_results)
                                        
                                elif any(term in search_query.lower() for term in ['structure', 'site list', 'build', 'create', 'generate']):
                                    # Extract criteria for site list structuring
                                    criteria = {}
                                    
                                    # Extract therapeutic area
                                    therapeutic_areas = ['cancer', 'oncology', 'diabetes', 'cardiovascular', 'neurology', 'immunology']
                                    for area in therapeutic_areas:
                                        if area in search_query.lower():
                                            criteria['therapeutic_area'] = area
                                            break
                                    
                                    # Extract geographic criteria
                                    if 'china' in search_query.lower():
                                        criteria['geographic_region'] = 'country:china'
                                    elif 'united states' in search_query.lower() or 'usa' in search_query.lower():
                                        criteria['geographic_region'] = 'country:united states'
                                    
                                    # Extract site type criteria
                                    if 'university' in search_query.lower():
                                        criteria['site_type'] = 'university'
                                    elif 'hospital' in search_query.lower():
                                        criteria['site_type'] = 'hospital'
                                    elif 'clinic' in search_query.lower():
                                        criteria['site_type'] = 'clinic'
                                    
                                    # Extract experience criteria
                                    import re
                                    min_exp_match = re.search(r'at least (\d+) trials', search_query, re.IGNORECASE)
                                    if min_exp_match:
                                        criteria['min_trial_experience'] = int(min_exp_match.group(1))
                                    
                                    max_exp_match = re.search(r'less than (\d+) trials', search_query, re.IGNORECASE)
                                    if max_exp_match:
                                        criteria['max_trial_experience'] = int(max_exp_match.group(1))
                                    
                                    # Extract capacity criteria
                                    if 'available capacity' in search_query.lower():
                                        criteria['has_ongoing_capacity'] = True
                                    
                                    # Extract sorting criteria
                                    if 'sort by' in search_query.lower():
                                        if 'capacity' in search_query.lower():
                                            criteria['sort_by'] = 'capacity_utilization'
                                        elif 'experience' in search_query.lower():
                                            criteria['sort_by'] = 'total_trials'
                                    
                                    if criteria:
                                        results = await agent.structure_site_list(criteria, max_results=max_results)
                                        if results and 'error' not in results:
                                            results = [results]  # Convert single result to list
                                        else:
                                            results = []
                                    else:
                                        # Fallback to site search
                                        results = await agent.search_sites(search_query, max_results=max_results)
                                        
                                elif any(term in search_query.lower() for term in ['trial selection', 'site selection', 'compare trials', 'selection patterns']):
                                    # Extract trial IDs for site selection comparison
                                    import re
                                    trial_ids = re.findall(r'\b\d+\b', search_query)
                                    if trial_ids and len(trial_ids) >= 2:
                                        trial_ids = [int(tid) for tid in trial_ids[:5]]  # Limit to 5 trial IDs
                                        results = await agent.compare_trial_site_selection(trial_ids)
                                        if results and 'error' not in results:
                                            results = [results]  # Convert single result to list
                                        else:
                                            results = []
                                    else:
                                        # Fallback to site search
                                        results = await agent.search_sites(search_query, max_results=max_results)
                                        
                                elif any(term in search_query.lower() for term in ['site dynamics', 'site performance', 'site analysis', 'individual site']):
                                    # Extract site ID or name for dynamics analysis
                                    import re
                                    site_id_match = re.search(r'site[_\s]*id[_\s]*(\d+)', search_query, re.IGNORECASE)
                                    if site_id_match:
                                        site_id = site_id_match.group(1)
                                        results = await agent.analyze_site_dynamics(site_id)
                                        if results and 'error' not in results:
                                            results = [results]  # Convert single result to list
                                        else:
                                            results = []
                                    else:
                                        # Try to extract site name
                                        site_name_patterns = [
                                            r'analyze (.+)',
                                            r'dynamics of (.+)',
                                            r'performance of (.+)'
                                        ]
                                        site_name = None
                                        for pattern in site_name_patterns:
                                            match = re.search(pattern, search_query, re.IGNORECASE)
                                            if match:
                                                site_name = match.group(1).strip()
                                                break
                                        
                                        if site_name:
                                            # Get site details first to find site ID
                                            site_details = await agent.get_site_details(site_name)
                                            if site_details:
                                                results = await agent.analyze_site_dynamics(site_details['site_id'])
                                                if results and 'error' not in results:
                                                    results = [results]
                                                else:
                                                    results = []
                                            else:
                                                results = []
                                        else:
                                            # Fallback to site search
                                            results = await agent.search_sites(search_query, max_results=max_results)
                                        
                                elif any(term in search_query.lower() for term in ['filter', 'with', 'that have', 'characteristics']):
                                    # Extract characteristics for filtered search
                                    characteristics = {}
                                    
                                    # Extract geographic filters
                                    if 'china' in search_query.lower():
                                        characteristics['country'] = 'china'
                                    elif 'united states' in search_query.lower() or 'usa' in search_query.lower():
                                        characteristics['country'] = 'united states'
                                    
                                    # Extract site type filters
                                    if 'university' in search_query.lower():
                                        characteristics['site_type'] = 'university'
                                    elif 'hospital' in search_query.lower():
                                        characteristics['site_type'] = 'hospital'
                                    elif 'clinic' in search_query.lower():
                                        characteristics['site_type'] = 'clinic'
                                    
                                    # Extract trial count filters
                                    
                                    min_trials_match = re.search(r'at least (\d+) trials', search_query, re.IGNORECASE)
                                    if min_trials_match:
                                        characteristics['min_trials'] = int(min_trials_match.group(1))
                                    
                                    max_trials_match = re.search(r'less than (\d+) trials', search_query, re.IGNORECASE)
                                    if max_trials_match:
                                        characteristics['max_trials'] = int(max_trials_match.group(1))
                                    
                                    # Extract capacity filters
                                    if 'ongoing trials' in search_query.lower():
                                        characteristics['has_ongoing_trials'] = True
                                    if 'available capacity' in search_query.lower():
                                        characteristics['has_available_capacity'] = True
                                    
                                    # Extract disease area filters
                                    disease_areas = ['cancer', 'oncology', 'diabetes', 'cardiovascular', 'neurology']
                                    for area in disease_areas:
                                        if area in search_query.lower():
                                            characteristics['disease_area'] = area
                                            break
                                    
                                    if characteristics:
                                        results = await agent.search_sites_by_characteristics(characteristics, max_results=max_results)
                                    else:
                                        # Fallback to site search
                                        results = await agent.search_sites(search_query, max_results=max_results)
                                        
                                elif any(term in search_query.lower() for term in ['geographic', 'geography', 'region', 'country', 'state', 'city']):
                                    results = await agent.analyze_geographic_distribution(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['capacity', 'available', 'utilization', 'ongoing', 'planned']):
                                    results = await agent.analyze_site_capacity(search_query, max_results=max_results)
                                elif any(term in search_query.lower() for term in ['trial', 'study', 'participating']):
                                    # Extract trial IDs from query if possible
                                    import re
                                    trial_ids = re.findall(r'\b\d+\b', search_query)
                                    if trial_ids:
                                        trial_ids = [int(tid) for tid in trial_ids[:5]]  # Limit to 5 trial IDs
                                        results = await agent.get_trial_site_relationships(trial_ids)
                                    else:
                                        results = await agent.search_sites(search_query, max_results=max_results)
                                else:
                                    # Default to site search
                                    results = await agent.search_sites(search_query, max_results=max_results)
                                
                                new_state["execution_results"][node.id] = results
                            elif source in LIVE_API_GRAPH_SOURCES:
                                agent = self.available_agents[source]
                                results = await agent.search(search_query, max_results=max_results)
                                new_state["execution_results"][node.id] = [r.dict() for r in results]
                            else:
                                # e.g. llm or uninitialized lazy agents
                                if agent is None:
                                    print(f"⚠️ Agent not initialized for source: {source}")
                                else:
                                    print(
                                        f"⚠️ No dynamic search handler for source: {source} "
                                        "(use another node type or a supported search source)."
                                    )
                                results = []
                                new_state["execution_results"][node.id] = []
                            
                            # Add results to context manager for enhanced context management
                            if results and new_state.get("context_manager"):
                                for result in results:
                                    # Handle different result types
                                    if hasattr(result, 'dict'):
                                        # Pydantic models (clinical trials, pubmed, etc.)
                                        result_dict = result.dict()
                                    elif isinstance(result, dict):
                                        # Already dictionaries (FDA labels, etc.)
                                        result_dict = result
                                    else:
                                        # Fallback for other types
                                        result_dict = {"content": str(result)}
                                    
                                    new_state["context_manager"].add_context_item(
                                        layer_type="search",
                                        content=result_dict,
                                        source=source,
                                        node_id=node.id,
                                        metadata={
                                            "search_query": search_query,
                                            "search_focus": search_focus,
                                            "max_results": max_results,
                                            "search_instructions": node.parameters.get("search_instructions", "")
                                        }
                                    )
                        elif not dr_search_skipped:
                            # Handle LLM-generated source names that don't match exactly
                            source_mapping = {
                                "clinical_trials_api": "clinical_trials",
                                "pubmed_api": "pubmed",
                                "biomcp_api": "biomcp",
                                "aact_database": "aact",
                                "trialtrove_database": "trialtrove",
                                "biomarker_database": "trialtrove",
                                "fda_api": "openfda",
                                "openfda_api": "openfda",
                                "drug_database": "openfda",
                                "ema": "ema_eu",
                                "ema_api": "ema_eu",
                                "eu_medicines": "ema_eu",
                                "epar": "ema_eu",
                                "ema_epi": "ema_eu",
                                "fda_labels_database": "fda_labels",
                                "drug_labels": "fda_labels",
                                "pharma_news": "google_search",
                                "industry_news": "google_search",
                                "fierce_pharma_api": "google_search",
                                "web_search": "google_search",
                                "google_search_api": "google_search",
                                "china_regulatory_api": "china_regulatory",
                                "cde_nmpa": "china_regulatory",
                                "china_nmpa": "china_regulatory",
                                "china_cde": "china_regulatory",
                                "nih_reporter_api": "nih_reporter",
                                "nih_grants": "nih_reporter",
                                "reporter": "nih_reporter",
                                "npi_registry_api": "npi_registry",
                                "nppes": "npi_registry",
                                "npi": "npi_registry",
                                "open_alex": "openalex",
                                "cross_ref": "crossref",
                                "ror_api": "ror",
                                "open_payments_api": "open_payments",
                                "eu_ctis_api": "eu_ctis",
                                "ctis": "eu_ctis",
                                "isrctn_api": "isrctn",
                                "cms_open_data_api": "cms_open_data",
                                "cms_data": "cms_open_data",
                                "cms-open-data": "cms_open_data",
                                "fda_datadashboard_api": "fda_datadashboard",
                                "fda_dashboard": "fda_datadashboard",
                                "fda-dashboard": "fda_datadashboard",
                                "good_rx": "goodrx",
                                "goodrx_api": "goodrx",
                                "aact_soa_search": "aact",
                                "studies_with_soa": "aact",
                            }
                            
                            mapped_source = source_mapping.get(source, source)
                            if mapped_source in self.available_agents:
                                agent = self.available_agents[mapped_source]
                                if mapped_source == "clinical_trials":
                                    results = await agent.search_studies(search_query, max_results=max_results)
                                    new_state["execution_results"][node.id] = [r.dict() for r in results]
                                elif mapped_source == "pubmed":
                                    results = await agent.search_publications(search_query, max_results=max_results)
                                    new_state["execution_results"][node.id] = [r.dict() for r in results]
                                elif mapped_source == "biomcp":
                                    results = await agent.search_data(search_query, max_results=max_results)
                                    new_state["execution_results"][node.id] = [r.dict() for r in results]
                                elif mapped_source == "aact":
                                    results = await agent.search_studies(search_query, max_results=max_results)
                                    new_state["execution_results"][node.id] = [r.dict() for r in results]
                                elif mapped_source == "openfda":
                                    results = await agent.search_drugs(search_query, max_results=max_results)
                                    new_state["execution_results"][node.id] = [r.dict() for r in results]
                                elif mapped_source == "ema_eu":
                                    results = await agent.search(search_query, max_results=max_results)
                                    new_state["execution_results"][node.id] = [r.dict() for r in results]
                                elif mapped_source == "google_search":
                                    # Get search instructions from node parameters
                                    search_instructions = node.parameters.get("search_instructions", "")
                                    results = await agent.search_web(search_query, search_instructions, max_results=max_results)
                                    new_state["execution_results"][node.id] = [r.dict() for r in results]
                                elif mapped_source == "china_regulatory":
                                    search_instructions = node.parameters.get("search_instructions", "")
                                    results = await agent.search_regulatory(
                                        search_query, search_instructions, max_results=max_results
                                    )
                                    new_state["execution_results"][node.id] = [r.dict() for r in results]
                                elif mapped_source == "trialtrove":
                                    results = await agent.search_studies(search_query, max_results=max_results)
                                    # Store TrialTrove results as objects, not dictionaries, for protocol generation compatibility
                                    new_state["execution_results"][node.id] = results
                                elif mapped_source == "fda_labels":
                                    results = await agent.search_labels(search_query, max_results=max_results)
                                    new_state["execution_results"][node.id] = results
                                    # FDA labels results are already dictionaries, no need to call .dict()
                                elif mapped_source == "goodrx":
                                    raw = (search_query or "").strip()
                                    if not raw:
                                        results = []
                                        new_state["execution_results"][node.id] = []
                                    else:
                                        drug_names = _split_goodrx_drug_names(raw)
                                        drug_limit = max(1, min(max_results, 10))
                                        drug_names = drug_names[:drug_limit]
                                        results = await agent.search_drugs(drug_names)
                                        new_state["execution_results"][node.id] = [
                                            r.dict() for r in results
                                        ]
                                elif mapped_source in LIVE_API_GRAPH_SOURCES:
                                    results = await agent.search(search_query, max_results=max_results)
                                    new_state["execution_results"][node.id] = [r.dict() for r in results]
                            else:
                                print(f"❌ Unknown source: {source}")
                                new_state["execution_results"][node.id] = []
                    
                    elif node.type == "analyze":
                        # Use LLM to analyze results from previous nodes
                        # In sequential execution, get data from all previous search nodes
                        input_data = []
                        for prev_node_id in plan.execution_order[:plan.execution_order.index(node.id)]:
                            if prev_node_id in new_state["execution_results"]:
                                prev_data = new_state["execution_results"][prev_node_id]
                                if isinstance(prev_data, list):
                                    input_data.extend(prev_data)
                                else:
                                    input_data.append(prev_data)
                        
                        # Analyzing results from previous nodes
                        
                        # Create a dynamic analysis prompt based on the node description and parameters.
                        # Planner JSON uses top-level analysis_type + string analysis_focus; older paths used nested dicts.
                        if isinstance(node.parameters, dict):
                            p = node.parameters
                            raw_focus = p.get("analysis_focus")
                            analysis_type = (p.get("analysis_type") or "").strip() or None
                            analysis_aspects: List[str] = []
                            if isinstance(raw_focus, dict):
                                if not analysis_type:
                                    analysis_type = (raw_focus.get("type") or "general").strip()
                                aspects_val = raw_focus.get("aspects")
                                if isinstance(aspects_val, list):
                                    analysis_aspects = [str(a) for a in aspects_val if a]
                                elif aspects_val:
                                    analysis_aspects = [str(aspects_val)]
                            elif isinstance(raw_focus, str) and raw_focus.strip():
                                analysis_aspects = [raw_focus.strip()]
                            if not analysis_type:
                                analysis_type = "general"
                        else:
                            print(f"⚠️ Node parameters is not a dict: {node.parameters}")
                            analysis_type = "general"
                            analysis_aspects = []
                        
                        # Convert input_data to JSON-serializable format for the prompt
                        def make_json_serializable(obj):
                            """Convert objects to JSON-serializable format"""
                            if hasattr(obj, 'dict'):
                                return obj.dict()
                            elif isinstance(obj, dict):
                                return obj
                            elif isinstance(obj, list):
                                return [make_json_serializable(item) for item in obj]
                            else:
                                return str(obj)
                        
                        # Convert sample data to JSON-serializable format
                        sample_data = input_data[:5] if isinstance(input_data, list) else [input_data]
                        serializable_sample_data = [make_json_serializable(item) for item in sample_data]
                        
                        # Step 1: LLM provides analysis parameters and instructions
                        analysis_plan_prompt = f"""
You are an expert clinical research analyst. Based on the analysis task, provide specific parameters and instructions for data analysis.

ORIGINAL QUERY: {new_state['query']}

ANALYSIS TASK: {node.description}

ANALYSIS TYPE: {analysis_type}

ANALYSIS ASPECTS: {', '.join(analysis_aspects) if analysis_aspects else 'Based on the analysis task description'}

SAMPLE DATA (for context only): {json.dumps(serializable_sample_data, indent=2)}

TOTAL DATA ITEMS: {len(input_data)}

INSTRUCTIONS:
1. Provide specific analysis parameters and instructions—especially **granular fields** (document titles, URLs, agency names, dates, article/section references, meeting/submission types) when the data is regulatory or comparative.
2. If ANALYSIS TYPE is **compare** (or the task contrasts jurisdictions/agencies), the plan must require **side-by-side extraction** per jurisdiction, **verbatim quotes** for definitions or procedural steps, and **no generic “both require quality”** summaries.
3. Focus on the analysis task described above and the original query.
4. Be explicit about what evidence from the raw items must appear in the downstream report.

Return ONLY valid JSON with analysis parameters:

{{
    "analysis_type": "specific_analysis_type",
    "focus_areas": ["area1", "area2", "area3"],
    "data_extraction": {{
        "fields_to_extract": ["field1", "field2"],
        "grouping_criteria": ["criteria1", "criteria2"],
        "filtering_criteria": {{"field": "value"}},
        "aggregation_methods": ["count", "percentage", "average"]
    }},
    "analysis_instructions": "Specific instructions for what patterns to look for",
    "output_format": "structured_summary|detailed_report|statistical_summary"
}}
"""
                        
                        # Get analysis plan from LLM (JSON plan; moderate token ceiling)
                        _plan_mt = min(
                            8192,
                            getattr(settings, "SYNTHESIS_MAX_TOKENS", llm_agent.max_tokens),
                        )
                        analysis_plan_response = await llm_agent.generate_response(
                            analysis_plan_prompt,
                            max_tokens=_plan_mt,
                        )
                        try:
                            analysis_plan = json.loads(analysis_plan_response)
                        except:
                            # Fallback plan
                            analysis_plan = {
                                "analysis_type": "general",
                                "focus_areas": ["patterns", "trends"],
                                "data_extraction": {
                                    "fields_to_extract": ["title", "condition", "sponsor"],
                                    "grouping_criteria": ["sponsor", "condition"],
                                    "filtering_criteria": {},
                                    "aggregation_methods": ["count"]
                                },
                                "analysis_instructions": "Look for common patterns and trends in the data",
                                "output_format": "structured_summary"
                            }
                        

                        
                        # Step 2: Execute data analysis based on LLM instructions
                        analysis_results = await self._execute_data_analysis(input_data, analysis_plan)
                        
                        # Get current date for context
                        current_date = datetime.now().strftime('%Y-%m-%d')
                        
                        # Step 3: LLM synthesizes the analysis results
                        # Extract raw data samples for synthesis (if available)
                        raw_data_for_synthesis = analysis_results.get("raw_data_sample", [])
                        
                        synthesis_prompt = f"""
You are an expert clinical research analyst. Synthesize the analysis results into a comprehensive report.

CURRENT DATE: {current_date}

ORIGINAL QUERY: {new_state['query']}

ANALYSIS TASK: {node.description}

ANALYSIS PLAN: {json.dumps(analysis_plan, indent=2)}

ANALYSIS RESULTS SUMMARY: {json.dumps({k: v for k, v in analysis_results.items() if k in ['analysis_type', 'focus_areas', 'data_summary', 'insights']}, indent=2)}

RAW DATA SAMPLES ({len(raw_data_for_synthesis)} items):
{json.dumps(raw_data_for_synthesis[:50], indent=2) if raw_data_for_synthesis else "No raw data samples available"}
{'[... and ' + str(len(raw_data_for_synthesis) - 50) + ' more items]' if len(raw_data_for_synthesis) > 50 else ''}

INSTRUCTIONS:
1. Produce a **specific, evidence-backed** report—not a high-level overview. Ground claims in **titles, URLs, identifiers, and short quotes** from RAW DATA SAMPLES and the analysis summary.
2. For **compare**-style tasks: use **Markdown tables** (rows = topic, columns = entity/jurisdiction) and cite sources per cell.
3. Focus on the analysis task and original query; preserve **procedural detail** (who, when, what must be filed, meeting types, GLP/IND touchpoints) when present in the data.
4. Use the specified output format from the analysis plan where applicable.
5. Consider temporal context when the analysis involves recent developments.
6. Write the entire report in English for the product UI (translate any non-English source material faithfully).

DATE CONTEXT:
- When the analysis involves "recent", "latest", "new", or similar terms, consider the current date above
- "Recent" typically means within the last 1-2 years from the current date
- "Latest" typically means within the last 6-12 months from the current date
- "New" typically means within the last 1-3 months from the current date
- Provide temporal context for findings and trends

ANALYSIS REPORT:
"""
                        
                        _report_mt = getattr(
                            settings, "SYNTHESIS_MAX_TOKENS", llm_agent.max_tokens
                        )
                        analysis_report = await llm_agent.generate_response(
                            synthesis_prompt,
                            max_tokens=_report_mt,
                        )
                        compression_brief = await maybe_compress_analysis_node_output(
                            new_state["query"], analysis_report, analysis_results
                        )
                        # Store analysis results as a list to maintain consistency with other nodes
                        analysis_result = {
                            "analysis": analysis_report,
                            "analysis_plan": analysis_plan,
                            "analysis_results": analysis_results,
                            "node_type": "analysis",
                            "node_id": node.id,
                        }
                        if compression_brief:
                            analysis_result["compression_brief"] = compression_brief
                        new_state["execution_results"][node.id] = [analysis_result]
                        
                        # Add analysis results to context manager
                        if new_state.get("context_manager"):
                            new_state["context_manager"].add_context_item(
                                layer_type="analysis",
                                content=analysis_result,
                                source="llm_analysis",
                                node_id=node.id,
                                metadata={
                                    "analysis_type": analysis_type,
                                    "analysis_aspects": analysis_aspects,
                                    "input_data_count": len(input_data)
                                }
                            )
                    
                    elif node.type == "synthesize":
                        # Synthesize all results from previous nodes
                        # In sequential execution, get data from all previous nodes
                        all_results = {}
                        for prev_node_id in plan.execution_order[:plan.execution_order.index(node.id)]:
                            if prev_node_id in new_state["execution_results"]:
                                all_results[prev_node_id] = new_state["execution_results"][prev_node_id]
                        
                        # Also include raw search results for better context
                        # Look for search nodes that might have been processed by analysis nodes
                        search_results = {}
                        for node_id, data in all_results.items():
                            # Check if this is a search node (not analysis/reasoning/extraction)
                            node_info = next((n for n in plan.nodes if n.id == node_id), None)
                            if node_info and node_info.type == "search":
                                source = node_info.parameters.get("source", node_id)
                                search_results[f"raw_{source}_data"] = data
                        
                        # Merge search results with analysis results
                        all_results.update(search_results)
                        
                        # ENHANCED: Extract SoA table data for better synthesis
                        soa_table_data = []
                        trial_summaries = []
                        
                        # Look for SoA data in search results
                        for node_id, data in all_results.items():
                            if isinstance(data, list):
                                for item in data:
                                    if isinstance(item, dict):
                                        # Check if this item has SoA tables (either in 'extracted', 'soa_tables', or 'extracted_tables')
                                        soa_tables = item.get('soa_tables', []) or item.get('extracted', []) or item.get('extracted_tables', [])
                                        if soa_tables:
                                            trial_summary = {
                                                'nct_id': item.get('nct_id', 'Unknown'),
                                                'title': item.get('title', 'Unknown'),
                                                'condition': item.get('condition', 'Unknown'),
                                                'phase': item.get('phase', 'Unknown'),
                                                'status': item.get('status', 'Unknown'),
                                                'sponsor': item.get('sponsor', 'Unknown'),
                                                'soa_table_count': item.get('soa_table_count', len(soa_tables))
                                            }
                                            trial_summaries.append(trial_summary)
                                            
                                            # Extract detailed SoA table data
                                            for soa_table in soa_tables:
                                                if isinstance(soa_table, dict) and 'table_data' in soa_table:
                                                    soa_table_data.append({
                                                        'nct_id': soa_table.get('nct_id', item.get('nct_id', 'Unknown')),
                                                        'table_title': soa_table.get('table_title', 'Unknown'),
                                                        'page_number': soa_table.get('page_number', 0),
                                                        'table_data': soa_table.get('table_data', []),
                                                        'confidence_score': soa_table.get('confidence_score', 0.0),
                                                        'extraction_method': soa_table.get('extraction_method', 'Unknown')
                                                    })

                        print(f"🔍 Data being passed to synthesis:")
                        print(f"  📊 Trial Summaries: {len(trial_summaries)} trials")
                        print(f"  📋 SoA Tables: {len(soa_table_data)} detailed tables")
                        
                        for source, data in all_results.items():
                            if isinstance(data, list) and data:
                                print(f"  {source}: {len(data)} items")
                                # Show sample of actual data being passed
                                sample = data[0] if isinstance(data[0], dict) else str(data[0])
                                if isinstance(sample, dict):
                                    if 'title' in sample:
                                        print(f"    Sample title: {sample['title'][:100]}...")
                                    elif 'analysis' in sample:
                                        print(f"    Analysis node: {sample['analysis'][:100]}...")
                                    elif 'soa_tables' in sample and sample['soa_tables']:
                                        print(f"    SoA tables: {len(sample['soa_tables'])} tables")
                                        # Show sample SoA table info
                                        first_soa = sample['soa_tables'][0]
                                        if isinstance(first_soa, dict):
                                            print(f"    Sample SoA: {first_soa.get('table_title', 'Unknown')} (Page {first_soa.get('page_number', 0)})")
                                    elif 'extracted' in sample and sample['extracted']:
                                        print(f"    Extracted content: {len(sample['extracted'])} items")
                                        # Show sample extracted content info
                                        first_extracted = sample['extracted'][0]
                                        if isinstance(first_extracted, dict):
                                            print(f"    Sample extracted: {first_extracted.get('table_title', 'Unknown')} (Page {first_extracted.get('page_number', 0)})")
                                    else:
                                        print(f"    Sample keys: {list(sample.keys())}")
                            elif isinstance(data, dict):
                                print(f"  {source}: dict with keys {list(data.keys())}")
                            else:
                                print(f"  {source}: {type(data)}")

                        
                        # Check if we have meaningful data to synthesize
                        meaningful_data = {}
                        for source, data in all_results.items():
                            if isinstance(data, list) and len(data) > 0:
                                # For analysis, extraction, and reasoning nodes, extract the actual content
                                if data and isinstance(data[0], dict) and "node_type" in data[0]:
                                    # This is a structured node result, extract the main content
                                    if data[0]["node_type"] == "analysis":
                                        _ar = {"analysis": data[0]["analysis"]}
                                        if data[0].get("compression_brief"):
                                            _ar["compression_brief"] = data[0]["compression_brief"]
                                        meaningful_data[source] = [_ar]
                                    elif data[0]["node_type"] == "extraction":
                                        meaningful_data[source] = [{"extracted": data[0]["extracted"]}]
                                    elif data[0]["node_type"] == "reasoning":
                                        meaningful_data[source] = [{"reasoning": data[0]["reasoning"]}]
                                    elif data[0]["node_type"] == "simulation":
                                        # Handle simulation data - pass the full simulation response
                                        meaningful_data[source] = data
                                        print(f"🧬 Found simulation data in {source}: {data[0].get('simulation_id', 'Unknown ID')}")
                                    else:
                                        meaningful_data[source] = data
                                # CRITICAL FIX: Handle site map data specifically
                                elif data and isinstance(data[0], dict) and "map_id" in data[0]:
                                    # This is site map data - preserve it completely
                                    meaningful_data[source] = data
                                    print(f"🗺️ Found site map data in {source}: {data[0].get('map_id', 'Unknown Map ID')}")
                                # CRITICAL FIX: Handle claims data specifically
                                elif data and isinstance(data[0], dict) and "diagnosis_code" in data[0]:
                                    # This is claims data - preserve it completely
                                    meaningful_data[source] = data
                                    print(f"💰 Found claims data in {source}: {len(data)} diagnosis codes")
                                # CRITICAL FIX: Handle SoA data specifically
                                elif data and isinstance(data[0], dict) and ("soa_tables" in data[0] or "extracted_tables" in data[0]):
                                    # This is SoA data - preserve it completely
                                    meaningful_data[source] = data
                                    print(f"📋 Found SoA data in {source}: {len(data)} items")
                                else:
                                    # This is raw search data (like AACT SoA results)
                                    meaningful_data[source] = data
                            elif isinstance(data, dict) and data:
                                meaningful_data[source] = data
                        
                        # DYNAMIC TRUNCATION: Calculate limits based on actual data sizes
                        data_sources = {}
                        if soa_table_data:
                            data_sources["soa_table_details"] = soa_table_data
                        if trial_summaries:
                            data_sources["trial_summaries"] = trial_summaries
                        
                        # Add simulation data to data sources for dynamic calculation
                        simulation_data = []
                        for source, data in meaningful_data.items():
                            if isinstance(data, list) and data and isinstance(data[0], dict):
                                if data[0].get("simulation_id"):
                                    simulation_data.extend(data)
                                    print(f"🧬 Adding simulation data from {source} to synthesis")
                        
                        if simulation_data:
                            data_sources["simulation_data"] = simulation_data
                        
                        # Add site map data to data sources for dynamic calculation
                        site_map_data = []
                        for source, data in meaningful_data.items():
                            if isinstance(data, list) and data and isinstance(data[0], dict):
                                if data[0].get("map_id"):
                                    site_map_data.extend(data)
                                    print(f"🗺️ Adding site map data from {source} to synthesis")
                                    print(f"🗺️ Site map details: {data[0].get('map_id')} with {len(data[0].get('sites', []))} sites")
                        
                        if site_map_data:
                            data_sources["site_map_data"] = site_map_data
                            print(f"🗺️ Total site map data sources: {len(site_map_data)}")
                        
                        # CRITICAL: Merge site map data into meaningful_data to ensure it's passed to synthesis
                        if site_map_data:
                            meaningful_data["site_map_data"] = site_map_data
                            print(f"🗺️ Merged site map data into meaningful_data for synthesis")
                            
                            # CRITICAL FIX: Also add site map data as a separate explicit source
                            for i, site_map_item in enumerate(site_map_data):
                                meaningful_data[f"site_map_explicit_{i}"] = [site_map_item]
                                print(f"🗺️ Added explicit site map source: site_map_explicit_{i}")
                        
                        # Add enhanced context to data sources for dynamic calculation
                        if new_state.get("context_manager"):
                            # Estimate context size for dynamic limits
                            context_manager = new_state["context_manager"]
                            context_items = []
                            for layer in context_manager.layers:
                                context_items.extend(layer.items)
                            data_sources["enhanced_context"] = context_items
                        
                        # Calculate dynamic limits based on actual data sizes
                        dynamic_limits = self._calculate_dynamic_limits(
                            data_sources,
                            target_max_tokens=settings.meaningful_data_truncation_token_budget(),
                        )
                        
                        # Apply dynamic truncation
                        if soa_table_data:
                            truncated_soa_data = self._truncate_soa_data_for_synthesis(
                                soa_table_data, 
                                dynamic_limits.get("soa_table_details")
                            )
                            meaningful_data["soa_table_details"] = truncated_soa_data
                            print(f"  📋 Added {len(truncated_soa_data)} SoA tables to synthesis data (original: {len(soa_table_data)})")
                        
                        if trial_summaries:
                            truncated_trial_summaries = self._truncate_trial_summaries_for_synthesis(
                                trial_summaries,
                                dynamic_limits.get("trial_summaries")
                            )
                            meaningful_data["trial_summaries"] = truncated_trial_summaries
                            print(f"  📊 Added {len(truncated_trial_summaries)} trial summaries to synthesis data (original: {len(trial_summaries)})")
                        
                        # Estimate post-truncation token count
                        post_truncation_tokens = 0
                        for source_name, data in meaningful_data.items():
                            if data:
                                post_truncation_tokens += self._estimate_data_tokens(data)
                        print(f"📊 Post-truncation data tokens: {post_truncation_tokens:,}")

                        shard_summaries_md, meaningful_data = await map_reduce_meaningful_data(
                            new_state["query"], meaningful_data
                        )
                        if shard_summaries_md:
                            print(f"🧩 Map-reduce shard summaries attached ({len(shard_summaries_md)} chars)")
                        
                        # Use enhanced context manager for synthesis
                        if new_state.get("context_manager"):
                            attn_method = settings.CONTEXT_ATTENTION_METHOD
                            if attn_method not in ("keyword", "bm25", "hybrid"):
                                attn_method = "keyword"
                            new_state["context_manager"].calculate_attention_weights(
                                method=attn_method,
                                hybrid_keyword_weight=settings.CONTEXT_HYBRID_KEYWORD_WEIGHT,
                            )
                            
                            context_limit = dynamic_limits.get("enhanced_context", 24)
                            structured_nct_ids = set()
                            for row in meaningful_data.get("trial_summaries") or []:
                                if isinstance(row, dict) and row.get("nct_id"):
                                    structured_nct_ids.add(str(row["nct_id"]))
                            for row in meaningful_data.get("soa_table_details") or []:
                                if isinstance(row, dict) and row.get("nct_id"):
                                    structured_nct_ids.add(str(row["nct_id"]))
                            compact_nct_ids = (
                                structured_nct_ids if settings.SYNTHESIS_COMPACT_SEARCH_TRIALS else set()
                            )
                            enhanced_context = new_state["context_manager"].get_context_for_synthesis(
                                max_items_per_layer=context_limit,
                                layer_char_budget=settings.effective_context_layer_char_budget(),
                                compact_nct_ids=compact_nct_ids,
                                bm25_pool_factor=max(1, settings.CONTEXT_BM25_POOL_FACTOR),
                            )
                            
                            current_date = datetime.now().strftime('%Y-%m-%d')
                            _reg_hint = regulatory_comparison_user_hint(new_state["query"])

                            user_lines = [
                                f"CURRENT DATE: {current_date}",
                                f"ORIGINAL QUERY: {new_state['query']}",
                            ]
                            _wa = ""
                            if new_state.get("context_manager"):
                                _wa = str(
                                    new_state["context_manager"].global_context.get(
                                        "deep_research_working_answer"
                                    )
                                    or ""
                                ).strip()
                            if _wa:
                                user_lines.extend(
                                    [
                                        "",
                                        "WORKING ANSWER (built incrementally after each evidence step — refine, correct, and unify with all data below; do not discard unless contradicted by stronger evidence):",
                                        _wa[: settings.working_answer_max_chars()],
                                        "",
                                        "PRIMARY OUTPUT INSTRUCTION: Treat the WORKING ANSWER as the backbone of your reply. Expand it into the final comprehensive answer: preserve its structure and claims unless ENHANCED CONTEXT or STRUCTURED data clearly contradicts them. Use the context sections mainly to add citations, dates, identifiers, and missing nuance — not to restart from scratch.",
                                        "",
                                    ]
                                )
                            if _reg_hint:
                                user_lines.extend(["", _reg_hint, ""])
                            else:
                                user_lines.append("")
                            user_lines.extend([
                                "ENHANCED CONTEXT WITH ATTENTION WEIGHTS:",
                                enhanced_context,
                                "(Rows that reference STRUCTURED_TRIAL_AND_SOA_DATA use the canonical JSON block below for full trial/SoA fields — avoid duplicating long trial text from both sections.)",
                            ])
                            if shard_summaries_md:
                                user_lines.extend(["", "MAP_REDUCE_SHARD_SUMMARIES:", shard_summaries_md, ""])

                            user_lines.extend([
                                "=" * 80,
                                "STRUCTURED_TRIAL_AND_SOA_DATA (canonical JSON for trials with SoA / summaries — use for schedules, visits, procedures):",
                                "=" * 80,
                                "",
                                "TRIAL SUMMARIES (DYNAMICALLY SELECTED):",
                                json.dumps(meaningful_data.get("trial_summaries", []), indent=2),
                                "",
                                "DETAILED SOA TABLES (DYNAMICALLY SELECTED):",
                                json.dumps(meaningful_data.get("soa_table_details", []), indent=2),
                                "",
                                "SIMULATION RESULTS (DYNAMICALLY SELECTED):",
                                json.dumps(meaningful_data.get("simulation_data", []), indent=2),
                                "",
                                "COMPREHENSIVE ANSWER (produce your full response below following the system instructions):",
                            ])
                            synthesis_user_content = "\n".join(user_lines)

                            system_prompt = CLINICAL_SYNTHESIS_SYSTEM_PROMPT
                            _sp_tok = self._estimate_tokens(system_prompt)
                            _soft = settings.synthesis_combined_prompt_soft_limit()
                            combined_est = self._estimate_tokens(system_prompt + "\n" + synthesis_user_content)
                            print(f"📏 Final synthesis estimated at {combined_est:,} tokens (system + user, POST-TRUNCATION)")

                            if combined_est > _soft:
                                print(
                                    f"⚠️ Warning: combined prompt (~{combined_est:,} tokens) exceeds soft limit ({_soft:,}); truncating user content..."
                                )
                                synthesis_user_content = self._progressive_truncation(
                                    synthesis_user_content,
                                    target_tokens=settings.synthesis_user_progressive_target_tokens(_sp_tok),
                                )
                                combined_est = self._estimate_tokens(system_prompt + "\n" + synthesis_user_content)
                                print(f"📏 After progressive truncation (user only): {combined_est:,} tokens")
                                if combined_est > _soft:
                                    print(f"🚨 Still too large, applying emergency truncation to user content...")
                                    synthesis_user_content = self._emergency_truncation(
                                        synthesis_user_content,
                                        target_tokens=settings.synthesis_user_emergency_target_tokens(_sp_tok),
                                    )
                                    combined_est = self._estimate_tokens(system_prompt + "\n" + synthesis_user_content)
                                    print(f"🚨 After emergency truncation: {combined_est:,} tokens")
                            else:
                                print(f"✅ Prompt size ({combined_est:,} tokens) is within safe limits")

                            synthesis_answer = await self._synthesis_with_fallback(
                                synthesis_user_content,
                                system_prompt=system_prompt,
                                use_prompt_cache=settings.ENABLE_ANTHROPIC_PROMPT_CACHE,
                            )
                            
                            # Structured citations with URLs for the frontend
                            citation_links: List[Dict[str, str]] = []
                            for layer in new_state["context_manager"].layers:
                                for item in layer.items:
                                    if item.attention_weight and item.attention_weight > 0.3:  # High attention items
                                        if isinstance(item.content, dict):
                                            link = citation_link_from_content(item.content, layer.layer_type)
                                            if link:
                                                citation_links.append(link)
                            citations = dedupe_citation_links(citation_links)
                            
                            synthesis = {
                                "answer": synthesis_answer,
                                "citations": citations,
                                "confidence": "high" if len(citations) > 3 else "medium" if len(citations) > 1 else "low",
                                "data_quality": f"Enhanced context with {len(new_state['context_manager'].layers)} layers and {sum(len(l.items) for l in new_state['context_manager'].layers)} total items"
                            }
                        else:
                            # Fallback to original synthesis method
                            if not meaningful_data:
                                print("⚠️ No meaningful data available for synthesis")
                                synthesis = {
                                    "answer": f"Analysis completed for '{new_state['query']}'. Unfortunately, no relevant clinical trial data was found in the databases searched. This could be due to: 1) The specific drug or condition being too new or rare, 2) Search terms not matching database content, 3) Data not yet being available in the searched sources.",
                                    "citations": [],
                                    "confidence": "low",
                                    "data_quality": "No relevant data found in searched sources"
                                }
                            else:
                                synthesis = await llm_agent.synthesize_results(new_state["query"], meaningful_data)
                        
                        new_state["execution_results"][node.id] = synthesis
                    
                    elif node.type == "reason":
                        # Apply reasoning based on the node description and parameters
                        print(f"🔍 Applying reasoning: {node.description}")
                        
                        # Get reasoning parameters
                        reasoning_type = node.parameters.get("reasoning_type", "general")
                        reasoning_focus = node.parameters.get("focus", [])
                        reasoning_context = node.parameters.get("context", "data")
                        
                        # Get relevant data for reasoning
                        reasoning_data = []
                        for prev_node_id in plan.execution_order[:plan.execution_order.index(node.id)]:
                            if prev_node_id in new_state["execution_results"]:
                                prev_data = new_state["execution_results"][prev_node_id]
                                if isinstance(prev_data, list):
                                    reasoning_data.extend(prev_data[:10])  # Increased from 5 to 10 items for reasoning
                                else:
                                    reasoning_data.append(prev_data)
                        
                        # Convert reasoning_data to JSON-serializable format
                        def make_json_serializable(obj):
                            """Convert objects to JSON-serializable format"""
                            if hasattr(obj, 'dict'):
                                return obj.dict()
                            elif isinstance(obj, dict):
                                return obj
                            elif isinstance(obj, list):
                                return [make_json_serializable(item) for item in obj]
                            else:
                                return str(obj)
                        
                        serializable_reasoning_data = [make_json_serializable(item) for item in reasoning_data]
                        
                        # Get current date for context
                        current_date = datetime.now().strftime('%Y-%m-%d')
                        
                        # Build dynamic reasoning prompt
                        reasoning_prompt = f"""
You are an expert clinical research analyst. Apply reasoning to the following data based on the specific reasoning requirements.

CURRENT DATE: {current_date}

ORIGINAL QUERY: {new_state['query']}

REASONING TASK: {node.description}

REASONING TYPE: {reasoning_type}

REASONING FOCUS: {', '.join(reasoning_focus) if reasoning_focus else 'Based on the reasoning task description'}

CONTEXT: {reasoning_context}

DATA FOR REASONING: {json.dumps(serializable_reasoning_data, indent=2)}

INSTRUCTIONS:
1. Apply logical reasoning based on the specific reasoning task
2. Consider the original query context
3. Focus on the reasoning type and focus areas specified
4. Provide insights and conclusions grounded in the **DATA FOR REASONING**—cite URLs, titles, or ids from items where applicable; avoid generic regulatory platitudes
5. Be analytical and evidence-based in your reasoning
6. Consider temporal context when reasoning involves recent developments

DATE CONTEXT:
- When the reasoning involves "recent", "latest", "new", or similar terms, consider the current date above
- "Recent" typically means within the last 1-2 years from the current date
- "Latest" typically means within the last 6-12 months from the current date
- "New" typically means within the last 1-3 months from the current date
- Provide temporal context for findings and trends

REASONING GUIDELINES:
- If reasoning about causality: Look for cause-effect relationships, confounding factors
- If reasoning about trends: Analyze patterns over time, identify drivers of change
- If reasoning about effectiveness: Compare outcomes, consider study quality, bias
- If reasoning about feasibility: Assess practical considerations, resource requirements
- If reasoning about implications: Consider broader impact, future directions
- If reasoning about gaps: Identify missing information, research needs
- If reasoning about temporal patterns: Consider the current date and recent developments

Apply the specific type of reasoning requested and provide structured insights.

REASONING ANALYSIS:
"""
                        
                        _reason_mt = getattr(
                            settings, "SYNTHESIS_MAX_TOKENS", llm_agent.max_tokens
                        )
                        reasoning = await llm_agent.generate_response(
                            reasoning_prompt,
                            max_tokens=_reason_mt,
                        )
                        # Store reasoning results as a list to maintain consistency with other nodes
                        reasoning_result = {
                            "reasoning": reasoning,
                            "node_type": "reasoning",
                            "node_id": node.id
                        }
                        new_state["execution_results"][node.id] = [reasoning_result]
                        
                        # Add reasoning results to context manager
                        if new_state.get("context_manager"):
                            new_state["context_manager"].add_context_item(
                                layer_type="reasoning",
                                content=reasoning_result,
                                source="llm_reasoning",
                                node_id=node.id,
                                metadata={
                                    "reasoning_type": reasoning_type,
                                    "reasoning_focus": reasoning_focus,
                                    "reasoning_context": reasoning_context
                                }
                            )
                    
                    elif node.type == "filter":
                        # Filter results from the most recent previous node
                        source_data = []
                        for prev_node_id in reversed(plan.execution_order[:plan.execution_order.index(node.id)]):
                            if prev_node_id in new_state["execution_results"]:
                                source_data = new_state["execution_results"][prev_node_id]
                                break
                        


                        
                        # Get filter parameters
                        filter_criteria = node.parameters.get("criteria", {})
                        filter_type = node.parameters.get("filter_type", "simple")
                        filter_conditions = node.parameters.get("conditions", [])
                        


                        
                        # Initialize filtering variables
                        filtering_criteria = filter_criteria
                        sorting_criteria = []
                        limit = 10
                        filtering_logic = "AND"
                        special_conditions = filter_conditions
                        
                        # Step 1: Apply filtering criteria
                        filtered_data = source_data
                        if filtering_criteria:
                            # Handle string criteria by using LLM to parse it intelligently
                            if isinstance(filtering_criteria, str):
                                
                                # Ensure we have sample data for the LLM prompt
                                sample_data = source_data[0] if source_data and isinstance(source_data, list) and len(source_data) > 0 else {}
                                
                                # Use LLM to parse the string criteria into proper filtering parameters
                                criteria_parsing_prompt = f"""
You are an expert data filtering assistant. Parse the following filter criteria string into specific filtering parameters.

FILTER CRITERIA: {filtering_criteria}

SAMPLE DATA STRUCTURE: {json.dumps(sample_data, indent=2)}

INSTRUCTIONS:
1. Analyze the filter criteria string and determine what filtering/sorting is needed
2. Convert it into a proper filtering_criteria dictionary
3. Consider common patterns like:
   - "most recent" → sort by date in descending order
   - "largest/smallest" → sort by size/number in ascending/descending order
   - "phase 3" → filter by phase
   - "active/recruiting" → filter by status
   - "diabetes/cancer" → filter by condition
   - "Eli Lilly/Novo Nordisk" → filter by sponsor

Return ONLY valid JSON with filtering parameters:

{{
    "filtering_criteria": {{"field": "value", "field2": "value2"}},
    "sorting_criteria": ["field1", "field2"],
    "sort_by": "field_name",
    "sort_order": "asc|desc",
    "limit": 10
}}

EXAMPLES:
- "most_recent_start_date" → {{"sort_by": "start_date", "sort_order": "desc"}}
- "largest_enrollment" → {{"sort_by": "enrollment", "sort_order": "desc"}}
- "smallest_trial" → {{"sort_by": "enrollment", "sort_order": "asc"}}
- "phase_3_trials" → {{"filtering_criteria": {{"phase": "phase"}}, "sort_by": "start_date", "sort_order": "desc"}}
- "active_diabetes_trials" → {{"filtering_criteria": {{"status": "active", "condition": "diabetes"}}, "sort_by": "start_date", "sort_order": "desc"}}

JSON Response:
"""
                                
                                try:
                                    import re
                                    
                                    # Get LLM response
                                    llm_response = await llm_agent.generate_structured_response(
                                        criteria_parsing_prompt,
                                        system_prompt="You are an expert data filtering assistant. Parse filter criteria into structured parameters."
                                    )
                                    
                                    # Clean and parse the response
                                    cleaned_response = re.sub(r'```json\s*', '', llm_response)
                                    cleaned_response = re.sub(r'```\s*$', '', cleaned_response)
                                    cleaned_response = re.sub(r'```\s*', '', cleaned_response)
                                    
                                    parsed_criteria = json.loads(cleaned_response)
                                    
                                    # Update the filtering_criteria with parsed values
                                    if "filtering_criteria" in parsed_criteria:
                                        filtering_criteria = parsed_criteria["filtering_criteria"]
                                    if "sort_by" in parsed_criteria:
                                        sorting_criteria = [parsed_criteria["sort_by"]] + sorting_criteria
                                    if "sort_order" in parsed_criteria:
                                        # Store sort order for later use
                                        sort_order = parsed_criteria["sort_order"]
                                    if "limit" in parsed_criteria:
                                        limit = parsed_criteria["limit"]
                                        
                                    # If we have sort_by in the parsed criteria, add it to filtering_criteria for sorting
                                    if "sort_by" in parsed_criteria:
                                        if not isinstance(filtering_criteria, dict):
                                            filtering_criteria = {}
                                        filtering_criteria["sort_by"] = parsed_criteria["sort_by"]
                                        filtering_criteria["sort_order"] = parsed_criteria.get("sort_order", "desc")
                                    
                                except Exception as e:
                                    print(f"❌ Error parsing criteria with LLM: {e}")
                                    # Fallback to simple sorting by the field mentioned
                                    if "smallest" in filtering_criteria.lower():
                                        filtering_criteria = {"sort_by": "enrollment", "sort_order": "asc"}
                                    elif "largest" in filtering_criteria.lower():
                                        filtering_criteria = {"sort_by": "enrollment", "sort_order": "desc"}
                                    elif "recent" in filtering_criteria.lower():
                                        filtering_criteria = {"sort_by": "start_date", "sort_order": "desc"}
                                    else:
                                        filtering_criteria = {"sort_by": filtering_criteria, "sort_order": "desc"}
                            
                            # Ensure filtering_criteria is a dictionary
                            if not isinstance(filtering_criteria, dict):
                                print(f"⚠️ Invalid filtering criteria type: {type(filtering_criteria)}")
                                filtering_criteria = {}
                            
                            if filtering_criteria:
                                filtered_data = []
                                for item in source_data:
                                    if isinstance(item, dict):
                                        include_item = True
                                        
                                        if filtering_logic == "AND":
                                            # All criteria must match
                                            for field, value in filtering_criteria.items():
                                                if not self._matches_criteria(item, field, value):
                                                    include_item = False
                                                    break
                                        else:  # OR logic
                                            # At least one criteria must match
                                            any_match = False
                                            for field, value in filtering_criteria.items():
                                                if self._matches_criteria(item, field, value):
                                                    any_match = True
                                                    break
                                            include_item = any_match
                                        
                                        if include_item:
                                            filtered_data.append(item)
                        
                        # Step 2: Apply special conditions
                        if special_conditions and filtered_data:
                            for condition in special_conditions:
                                condition_lower = condition.lower()
                                if "active" in condition_lower or "recruiting" in condition_lower:
                                    # Filter for active/recruiting trials
                                    filtered_data = [
                                        item for item in filtered_data 
                                        if isinstance(item, dict) and (
                                            "status" in item and any(status in str(item["status"]).lower() 
                                                           for status in ["active", "recruiting", "ongoing"])
                                        )
                                    ]
                                elif "recent" in condition_lower:
                                    # Filter for recent trials (last 2 years)
                                    cutoff_date = datetime.now() - timedelta(days=730)
                                    filtered_data = [
                                        item for item in filtered_data 
                                        if isinstance(item, dict) and (
                                            # Check multiple possible date fields
                                            ("start_date" in item and item["start_date"] and item["start_date"] > cutoff_date.strftime("%Y-%m-%d")) or
                                            ("submission_status_date" in item and item["submission_status_date"] and item["submission_status_date"] > cutoff_date.strftime("%Y%m%d")) or
                                            ("approval_date" in item and item["approval_date"] and item["approval_date"] > cutoff_date.strftime("%Y-%m-%d")) or
                                            # If no date field found, include the item
                                            ("start_date" not in item and "submission_status_date" not in item and "approval_date" not in item)
                                        )
                                    ]
                                elif "large" in condition_lower or "enrollment" in condition_lower:
                                    # Filter for large trials
                                    filtered_data = [
                                        item for item in filtered_data 
                                        if isinstance(item, dict) and (
                                            "enrollment" not in item or 
                                            (item["enrollment"] and item["enrollment"] > 100)
                                        )
                                    ]
                                elif "phase3" in condition_lower or "phase 3" in condition_lower:
                                    # Filter for Phase 3 trials
                                    filtered_data = [
                                        item for item in filtered_data 
                                        if isinstance(item, dict) and (
                                            "phase" in item and "phase3" in str(item["phase"]).lower()
                                        )
                                    ]
                                elif "completed" in condition_lower:
                                    # Filter for completed trials
                                    filtered_data = [
                                        item for item in filtered_data 
                                        if isinstance(item, dict) and (
                                            "status" in item and "completed" in str(item["status"]).lower()
                                        )
                                    ]
                                elif "diabetes" in condition_lower:
                                    # Filter for diabetes trials
                                    filtered_data = [
                                        item for item in filtered_data 
                                        if isinstance(item, dict) and (
                                            "condition" in item and "diabetes" in str(item["condition"]).lower()
                                        )
                                    ]
                                elif "lilly" in condition_lower or "eli" in condition_lower:
                                    # Filter for Eli Lilly trials
                                    filtered_data = [
                                        item for item in filtered_data 
                                        if isinstance(item, dict) and (
                                            "sponsor" in item and "lilly" in str(item["sponsor"]).lower()
                                        )
                                    ]
                        
                        # Step 3: Apply sorting
                        if sorting_criteria and filtered_data:
                            def sort_key(item):
                                if not isinstance(item, dict):
                                    return ""
                                key_parts = []
                                for criterion in sorting_criteria:
                                    if criterion in item:
                                        key_parts.append(str(item[criterion]))
                                    else:
                                        key_parts.append("")
                                return " | ".join(key_parts)
                            
                            filtered_data.sort(key=sort_key)
                        
                        # Also check for sorting criteria in the filtering_criteria
                        if isinstance(filtering_criteria, dict) and filtering_criteria.get("sort_by"):
                            sort_field = filtering_criteria.get("sort_by")
                            sort_order = filtering_criteria.get("sort_order", "desc")
                            
                            print(f"📊 Applying sorting: {sort_field} in {sort_order} order")
                            
                            def sort_key(item):
                                if not isinstance(item, dict):
                                    return ""
                                if sort_field in item:
                                    value = item[sort_field]
                                    # Handle date sorting
                                    if isinstance(value, str) and "-" in value:
                                        try:
                                            return datetime.strptime(value, "%Y-%m-%d")
                                        except:
                                            return value
                                    # Handle numeric sorting
                                    try:
                                        return float(value) if value else 0
                                    except:
                                        return str(value) if value else ""
                                return ""
                            
                            filtered_data.sort(key=sort_key, reverse=(sort_order.lower() == "desc"))
                        
                        # Step 4: Apply limit
                        if limit > 0 and len(filtered_data) > limit:
                            filtered_data = filtered_data[:limit]
                        
                        # Create results structure
                        results = {
                            "filter_type": filter_type,
                            "filtering_criteria": filtering_criteria,
                            "filtered_data": filtered_data,
                            "summary": {
                                "total_items": len(source_data),
                                "filtered_items": len(filtered_data),
                                "reduction_percentage": (
                                    (len(source_data) - len(filtered_data)) / len(source_data) * 100 if len(source_data) > 0 else 0
                                )
                            },
                            "insights": []
                        }
                        
                        # Step 5: Generate insights
                        results["insights"].append(f"Filtered {len(source_data)} items to {len(filtered_data)} items")
                        if filtering_criteria:
                            results["insights"].append(f"Applied {len(filtering_criteria)} filtering criteria")
                        if special_conditions:
                            results["insights"].append(f"Applied {len(special_conditions)} special conditions")
                        if sorting_criteria:
                            results["insights"].append(f"Sorted by {', '.join(sorting_criteria)}")
                        
                        # Store filter results as a list to maintain consistency with other nodes
                        # The actual filtered data should be the main content
                        if isinstance(filtered_data, list):
                            new_state["execution_results"][node.id] = filtered_data
                        else:
                            new_state["execution_results"][node.id] = [results]
                    
                    elif node.type == "extract":
                        # Extract specific information from the most recent previous node
                        source_data = []
                        for prev_node_id in reversed(plan.execution_order[:plan.execution_order.index(node.id)]):
                            if prev_node_id in new_state["execution_results"]:
                                source_data = new_state["execution_results"][prev_node_id]
                                break
                        
                    elif node.type in ("protocol_generate", "protocol_full"):
                        print(
                            f"⚠️ Node type {node.type} is disabled in dynamic chat (node_id={node.id})"
                        )
                        new_state["execution_results"][node.id] = [{
                            "skipped": True,
                            "reason": "protocol_authoring_disabled",
                            "content": (
                                "Protocol drafting is not available in this chat. "
                                "Use search results and the synthesis step for evidence summaries."
                            ),
                            "node_type": node.type,
                            "node_id": node.id,
                        }]
                    
                    elif node.type == "simulation":
                        print(f"🧬 Starting clinical trial simulation for node: {node.id}")
                        
                        # Add simulation to execution trace
                        new_state["execution_trace"].append({
                            "node_id": node.id,
                            "node_type": "simulation",
                            "status": "started",
                            "description": "Running clinical trial simulation with MCMC modeling",
                            "start_time": datetime.now().isoformat()
                        })
                        
                        # Create simulation request from query and conversation history
                        from agents.simulation_agent import SimulationRequest
                        
                        # Get query from the original query or node parameters
                        simulation_query = new_state.get("query", node.parameters.get("query", "Run clinical trial simulation"))
                        conversation_history = new_state.get("conversation_history", [])
                        
                        # Create simulation request
                        simulation_request = SimulationRequest(
                            query=simulation_query,
                            conversation_history=conversation_history,
                            execution_mode="dynamic"
                        )
                        
                        # Create progress callback for simulation
                        async def simulation_progress_callback(progress_data):
                            # Update execution trace with simulation progress
                            if "node_id" in progress_data:
                                # Find existing trace entry
                                for entry in new_state["execution_trace"]:
                                    if entry.get("node_id") == progress_data["node_id"]:
                                        entry.update(progress_data)
                                        break
                                else:
                                    # Add new entry if not found
                                    new_state["execution_trace"].append(progress_data)
                            
                            # Call main progress callback
                            if progress_callback:
                                await progress_callback(progress_data)
                        
                        try:
                            # Run the simulation
                            print(f"🧬 🚀 Calling simulation_agent.run_simulation with query: {simulation_query}")
                            simulation_response = await simulation_agent.run_simulation(simulation_request)
                            print(f"🧬 ✅ Simulation response received: {simulation_response.simulation_id}")
                            print(f"🧬 📊 Simulation results keys: {list(simulation_response.results.keys()) if simulation_response.results else 'No results'}")
                            
                            # Store simulation results
                            simulation_data = simulation_response.dict()
                            print(f"🧬 💾 Storing simulation data in execution_results[{node.id}]")
                            print(f"🧬 📊 Simulation data keys: {list(simulation_data.keys())}")
                            print(f"🧬 🆔 Simulation ID: {simulation_data.get('simulation_id')}")
                            print(f"🧬 📈 Results keys: {list(simulation_data.get('results', {}).keys())}")
                            new_state["execution_results"][node.id] = [simulation_data]
                            
                            # Update execution trace with completion
                            for entry in new_state["execution_trace"]:
                                if entry.get("node_id") == node.id:
                                    entry.update({
                                        "status": "completed",
                                        "description": f"Completed clinical trial simulation (ID: {simulation_response.simulation_id})",
                                        "end_time": datetime.now().isoformat(),
                                        "execution_time": simulation_response.execution_time_seconds
                                    })
                                    break
                            
                            print(f"🧬 ✅ Simulation completed successfully: {simulation_response.simulation_id}")
                            
                        except Exception as e:
                            print(f"❌ Simulation failed: {e}")
                            import traceback
                            print(f"❌ Simulation error traceback: {traceback.format_exc()}")
                            
                            # Store error result
                            new_state["execution_results"][node.id] = [{
                                "error": str(e),
                                "simulation_id": f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                "status": "error",
                                "node_type": "simulation",
                                "node_id": node.id
                            }]
                            
                            # Update execution trace with error
                            for entry in new_state["execution_trace"]:
                                if entry.get("node_id") == node.id:
                                    entry.update({
                                        "status": "error",
                                        "description": f"Simulation failed: {str(e)}",
                                        "end_time": datetime.now().isoformat(),
                                        "error": str(e)
                                    })
                                    break
                    
                    elif node.type == "site_map":
                        print(f"🗺️ Starting site map generation for node: {node.id}")
                        
                        # Add site map to execution trace
                        new_state["execution_trace"].append({
                            "node_id": node.id,
                            "node_type": "site_map",
                            "status": "started",
                            "description": "Generating interactive site map with population overlays",
                            "start_time": datetime.now().isoformat()
                        })
                        
                        try:
                            # Create site map request from query and conversation history
                            from models.schemas import SiteMapRequest
                            
                            # Get query from the original query or node parameters
                            site_map_query = new_state.get("query", node.parameters.get("query", "Generate site map"))
                            conversation_history = new_state.get("conversation_history", [])
                            
                            # Extract parameters from node if available
                            therapeutic_area = node.parameters.get("therapeutic_area")
                            inclusion_criteria = node.parameters.get("inclusion_criteria", [])
                            exclusion_criteria = node.parameters.get("exclusion_criteria", [])
                            geographic_scope = node.parameters.get("geographic_scope")
                            site_filters = node.parameters.get("site_filters")
                            population_filters = node.parameters.get("population_filters")
                            
                            # Convert geographic_scope string to dict if needed
                            if isinstance(geographic_scope, str):
                                geographic_scope = {"country": geographic_scope, "region": "all"}
                            elif geographic_scope is None:
                                geographic_scope = {"country": "United States", "region": "all"}
                            
                            # Convert site_filters string to dict if needed
                            if isinstance(site_filters, str):
                                site_filters = {"type": site_filters}
                            elif site_filters is None:
                                site_filters = {}
                            
                            # Convert population_filters string to dict if needed
                            if isinstance(population_filters, str):
                                population_filters = {"demographic": population_filters}
                            elif population_filters is None:
                                population_filters = {}
                            
                            # Create site map request
                            site_map_request = SiteMapRequest(
                                query=site_map_query,
                                therapeutic_area=therapeutic_area,
                                inclusion_criteria=inclusion_criteria,
                                exclusion_criteria=exclusion_criteria,
                                geographic_scope=geographic_scope,
                                site_filters=site_filters,
                                population_filters=population_filters,
                                conversation_history=conversation_history
                            )
                            
                            # Call site map agent
                            print(f"🗺️ Calling site map agent with request: {site_map_request.query}")
                            site_map_response = await self.available_agents["site_map"].generate_site_map(site_map_request)
                            
                            # Store site map results
                            site_map_data = site_map_response.dict()
                            print(f"🗺️ 💾 Storing site map data in execution_results[{node.id}]")
                            print(f"🗺️ 📊 Site map data keys: {list(site_map_data.keys())}")
                            print(f"🗺️ 🆔 Map ID: {site_map_data.get('map_id')}")
                            print(f"🗺️ 📍 Sites found: {len(site_map_data.get('sites', []))}")
                            new_state["execution_results"][node.id] = [site_map_data]
                            
                            # Update execution trace with completion
                            for entry in new_state["execution_trace"]:
                                if entry.get("node_id") == node.id:
                                    entry.update({
                                        "status": "completed",
                                        "description": f"Completed site map generation (ID: {site_map_response.map_id}, {len(site_map_response.sites)} sites)",
                                        "end_time": datetime.now().isoformat(),
                                        "sites_count": len(site_map_response.sites)
                                    })
                                    break
                            
                            print(f"🗺️ ✅ Site map generation completed successfully: {site_map_response.map_id}")
                            
                        except Exception as e:
                            print(f"❌ Site map generation failed: {e}")
                            import traceback
                            print(f"❌ Site map error traceback: {traceback.format_exc()}")
                            
                            # Store error result
                            new_state["execution_results"][node.id] = [{
                                "error": str(e),
                                "map_id": f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                "status": "error",
                                "node_type": "site_map",
                                "node_id": node.id
                            }]
                            
                            # Update execution trace with error
                            for entry in new_state["execution_trace"]:
                                if entry.get("node_id") == node.id:
                                    entry.update({
                                        "status": "error",
                                        "description": f"Site map generation failed: {str(e)}",
                                        "end_time": datetime.now().isoformat(),
                                        "error": str(e)
                                    })
                                    break
                    
                    # elif node.type == "hitl_trial_selection":
                    #     # HITL trial selection is disabled
                    #     print(f"🎯 HITL trial selection disabled for node: {node.id}")
                    #     new_state["execution_results"][node.id] = []
                    
                    elif node.type == "extract":
                        # Extract specific information from the most recent previous node
                        source_data = []
                        for prev_node_id in reversed(plan.execution_order[:plan.execution_order.index(node.id)]):
                            if prev_node_id in new_state["execution_results"]:
                                source_data = new_state["execution_results"][prev_node_id]
                                break
                        
                        # Get extraction parameters
                        if isinstance(node.parameters, dict):
                            extraction_target = node.parameters.get("target", "key information")
                            extraction_format = node.parameters.get("format", "text")
                            extraction_focus = node.parameters.get("focus", [])
                        else:
                            print(f"⚠️ Node parameters is not a dict: {node.parameters}")
                            extraction_target = "key information"
                            extraction_format = "text"
                            extraction_focus = []
                        
                        # Convert source_data to JSON-serializable format
                        def make_json_serializable(obj):
                            """Convert objects to JSON-serializable format"""
                            if hasattr(obj, 'dict'):
                                return obj.dict()
                            elif isinstance(obj, dict):
                                return obj
                            elif isinstance(obj, list):
                                return [make_json_serializable(item) for item in obj]
                            else:
                                return str(obj)
                        
                        # Convert sample data to JSON-serializable format
                        sample_data = source_data[:5] if isinstance(source_data, list) else [source_data]
                        serializable_sample_data = [make_json_serializable(item) for item in sample_data]
                        
                        # Get current date for context
                        current_date = datetime.now().strftime('%Y-%m-%d')
                        
                        # Step 1: LLM provides extraction parameters and instructions
                        extraction_plan_prompt = f"""
You are an expert clinical research data extractor. Based on the extraction task, provide specific parameters for data extraction.

CURRENT DATE: {current_date}

ORIGINAL QUERY: {new_state['query']}

EXTRACTION TASK: {node.description}

TARGET INFORMATION: {extraction_target}

EXTRACTION FOCUS: {', '.join(extraction_focus) if extraction_focus else 'Based on the extraction task description'}

OUTPUT FORMAT: {extraction_format}

SAMPLE DATA (for context only): {json.dumps(serializable_sample_data, indent=2)}

TOTAL DATA ITEMS: {len(source_data) if isinstance(source_data, list) else 1}

INSTRUCTIONS:
1. Provide specific extraction parameters and instructions
2. Focus on the extraction task described above
3. Consider the original query context
4. Be specific about what fields to extract and how to format them
5. Consider temporal context when the extraction involves recent developments

DATE CONTEXT:
- When the extraction involves "recent", "latest", "new", or similar terms, consider the current date above
- "Recent" typically means within the last 1-2 years from the current date
- "Latest" typically means within the last 6-12 months from the current date
- "New" typically means within the last 1-3 months from the current date

Return ONLY valid JSON with extraction parameters:

{{
    "extraction_type": "specific_extraction_type",
    "target_fields": ["field1", "field2", "field3"],
    "filtering_criteria": {{"field": "value"}},
    "grouping_criteria": ["criteria1", "criteria2"],
    "formatting_instructions": "Specific formatting instructions",
    "output_structure": "list|table|summary|detailed"
}}
"""
                        
                        # Get extraction plan from LLM
                        extraction_plan_response = await llm_agent.generate_response(extraction_plan_prompt)
                        try:
                            extraction_plan = json.loads(extraction_plan_response)
                        except:
                            # Fallback plan
                            extraction_plan = {
                                "extraction_type": "general",
                                "target_fields": ["title", "condition", "sponsor"],
                                "filtering_criteria": {},
                                "grouping_criteria": [],
                                "formatting_instructions": "Extract key information in a structured format",
                                "output_structure": "list"
                            }
                        
                        print(f"📊 Extraction plan: {extraction_plan}")
                        
                        # Step 2: Execute data extraction based on LLM instructions
                        extraction_results = await self._execute_data_extraction(source_data, extraction_plan)
                        
                        # Step 3: LLM formats the extraction results
                        formatting_prompt = f"""
You are an expert clinical research data formatter. Format the extraction results according to the specified requirements.

CURRENT DATE: {current_date}

ORIGINAL QUERY: {new_state['query']}

EXTRACTION TASK: {node.description}

EXTRACTION PLAN: {json.dumps(extraction_plan, indent=2)}

EXTRACTION RESULTS SUMMARY: {json.dumps({k: v for k, v in extraction_results.items() if k in ['extraction_type', 'target_fields', 'summary', 'insights']}, indent=2)}

INSTRUCTIONS:
1. Format the extraction results according to the specified output structure
2. Focus on the extraction task and original query
3. Make the output clear and actionable
4. Follow the formatting instructions provided
5. Consider temporal context when formatting involves recent developments

DATE CONTEXT:
- When the formatting involves "recent", "latest", "new", or similar terms, consider the current date above
- "Recent" typically means within the last 1-2 years from the current date
- "Latest" typically means within the last 6-12 months from the current date
- "New" typically means within the last 1-3 months from the current date
- Provide temporal context for findings when relevant

FORMATTED EXTRACTION:
"""
                        
                        formatted_extraction = await llm_agent.generate_response(formatting_prompt)
                        # Store extraction results as a list to maintain consistency with other nodes
                        new_state["execution_results"][node.id] = [{
                            "extracted": formatted_extraction,
                            "extraction_plan": extraction_plan,
                            "extraction_results": extraction_results,
                            "node_type": "extraction",
                            "node_id": node.id
                        }]
                    
                    # Update execution trace
                    new_state["execution_trace"][-1]["end_time"] = datetime.now().isoformat()
                    new_state["execution_trace"][-1]["success"] = True

                    try:
                        self._record_node_artifact(new_state, node)
                    except Exception as art_err:
                        print(f"⚠️ Node artifact skipped: {art_err}")
                    
                    # Call progress callback if provided
                    if progress_callback:
                        print(f"🔔 Progress callback called for node: {node.id}")
                        
                        # Safely get start_time and end_time from execution trace
                        start_time = None
                        end_time = None
                        
                        # Find the execution trace entry for this specific node
                        node_trace_entry = None
                        for trace_entry in new_state["execution_trace"]:
                            if trace_entry.get("node_id") == node.id:
                                node_trace_entry = trace_entry
                                break
                        
                        if node_trace_entry:
                            start_time = node_trace_entry.get("start_time")
                            end_time = node_trace_entry.get("end_time")
                        elif new_state["execution_trace"]:
                            # Fallback to last trace entry
                            last_trace = new_state["execution_trace"][-1]
                            start_time = last_trace.get("start_time")
                            end_time = last_trace.get("end_time")
                        
                        # Use fallback values if not found
                        if not start_time:
                            start_time = datetime.now().isoformat()
                        if not end_time:
                            end_time = datetime.now().isoformat()
                        
                        progress_data = {
                            "node_id": node.id,
                            "node_type": node.type,
                            "status": "completed",
                            "start_time": start_time,
                            "end_time": end_time,
                            "description": node.description,
                            "error": ""
                        }
                        
                        try:
                            await progress_callback(progress_data)
                            print(f"✅ Progress callback completed for node: {node.id}")
                        except Exception as e:
                            print(f"⚠️ Error calling progress callback: {e}")
                            print(f"🔍 Debug - Node ID: {node.id}, Start Time: {start_time}, End Time: {end_time}")
                            print(f"🔍 Debug - Execution trace entries: {len(new_state['execution_trace'])}")
                            for i, trace in enumerate(new_state["execution_trace"]):
                                print(f"🔍 Debug - Trace {i}: {trace.get('node_id', 'N/A')} - {trace.get('start_time', 'N/A')}")
                    else:
                        print(f"⚠️ No progress callback provided for node: {node.id}")

                    if incremental_dr and incremental_dr.get("enabled") and new_state.get("context_manager"):
                        if node.type in ("search", "analyze", "extract"):
                            try:
                                await self._deep_research_after_evidence_step(
                                    incremental_dr,
                                    new_state,
                                    node,
                                    plan,
                                    progress_callback,
                                )
                            except Exception as dr_inc_err:
                                log_error(dr_inc_err, "deep_research incremental step")
                    
                    return new_state
                    
                except Exception as e:
                    log_error(e, f"Node execution: {node.id}")
                    new_state["execution_trace"][-1]["end_time"] = datetime.now().isoformat()
                    new_state["execution_trace"][-1]["success"] = False
                    new_state["execution_trace"][-1]["error"] = str(e)
                    new_state["error"] = f"Node {node.id} failed: {str(e)}"
                    
                    # Call progress callback for failed node if provided
                    if progress_callback:
                        # Safely get start_time and end_time from execution trace
                        start_time = None
                        end_time = None
                        
                        # Find the execution trace entry for this specific node
                        node_trace_entry = None
                        for trace_entry in new_state["execution_trace"]:
                            if trace_entry.get("node_id") == node.id:
                                node_trace_entry = trace_entry
                                break
                        
                        if node_trace_entry:
                            start_time = node_trace_entry.get("start_time")
                            end_time = node_trace_entry.get("end_time")
                        elif new_state["execution_trace"]:
                            # Fallback to last trace entry
                            last_trace = new_state["execution_trace"][-1]
                            start_time = last_trace.get("start_time")
                            end_time = last_trace.get("end_time")
                        
                        # Use fallback values if not found
                        if not start_time:
                            start_time = datetime.now().isoformat()
                        if not end_time:
                            end_time = datetime.now().isoformat()
                        
                        progress_data = {
                            "node_id": node.id,
                            "node_type": node.type,
                            "status": "failed",
                            "start_time": start_time,
                            "end_time": end_time,
                            "description": node.description,
                            "error": str(e)
                        }
                        try:
                            await progress_callback(progress_data)
                        except Exception as callback_error:
                            print(f"⚠️ Error calling progress callback: {callback_error}")
                    
                    return new_state
            
            return node_function
        
        # Create the graph
        graph = StateGraph(DynamicGraphState)
        
        # Add nodes
        for node in plan.nodes:
            graph.add_node(node.id, create_node_function(node))
        
        # Debug prints


        
        # Connect START to the first node in execution order
        if plan.execution_order:
            first_node = plan.execution_order[0]
            graph.add_edge(START, first_node)
    
        
        # Connect nodes in execution order sequence (sequential execution)
        for i in range(len(plan.execution_order) - 1):
            current_node = plan.execution_order[i]
            next_node = plan.execution_order[i + 1]
            graph.add_edge(current_node, next_node)
            
        
        # Add end condition - connect last node to END
        if plan.execution_order:
            last_node = plan.execution_order[-1]
            graph.add_edge(last_node, END)
    
        
        return graph.compile()
    
    async def _execute_data_analysis(self, data: List[Any], analysis_plan: Dict) -> Dict:
        """Execute data analysis based on LLM-provided instructions"""
        try:
            results = {
                "analysis_type": analysis_plan.get("analysis_type", "general"),
                "focus_areas": analysis_plan.get("focus_areas", []),
                "data_summary": {},
                "patterns": {},
                "statistics": {},
                "insights": []
            }
            
            if not data:
                results["insights"].append("No data available for analysis")
                return results
            
            # Convert data to JSON-serializable format for analysis
            def make_json_serializable(obj):
                """Convert objects to JSON-serializable format"""
                if hasattr(obj, 'dict'):
                    return obj.dict()
                elif isinstance(obj, dict):
                    return obj
                elif isinstance(obj, list):
                    return [make_json_serializable(item) for item in obj]
                else:
                    return str(obj)
            
            # Convert all data items to serializable format
            serializable_data = [make_json_serializable(item) for item in data]
            
            # Limit data size to prevent memory issues
            max_data_items = 1000
            if len(serializable_data) > max_data_items:
                serializable_data = serializable_data[:max_data_items]
                results["insights"].append(f"Limited analysis to {max_data_items} items from {len(data)} total")
            
            # Extract data extraction parameters
            extraction = analysis_plan.get("data_extraction", {})
            fields_to_extract = extraction.get("fields_to_extract", [])
            grouping_criteria = extraction.get("grouping_criteria", [])
            filtering_criteria = extraction.get("filtering_criteria", {})
            aggregation_methods = extraction.get("aggregation_methods", ["count"])
            
            # Step 1: Filter data based on criteria
            filtered_data = serializable_data
            if filtering_criteria:
                filtered_data = []
                for item in serializable_data:
                    if isinstance(item, dict):
                        include_item = True
                        for field, value in filtering_criteria.items():
                            if field in item:
                                # Handle string matching
                                if isinstance(value, str) and isinstance(item[field], str):
                                    if value.lower() not in item[field].lower():
                                        include_item = False
                                        break
                                elif item[field] != value:
                                    include_item = False
                                    break
                            else:
                                # Try to find similar field names
                                found = False
                                for key in item.keys():
                                    if field.lower() in key.lower() or key.lower() in field.lower():
                                        if isinstance(value, str) and isinstance(item[key], str):
                                            if value.lower() in item[key].lower():
                                                found = True
                                                break
                                        elif item[key] == value:
                                            found = True
                                            break
                                if not found:
                                    include_item = False
                                    break
                        if include_item:
                            filtered_data.append(item)
            
            results["data_summary"]["total_items"] = len(serializable_data)
            results["data_summary"]["filtered_items"] = len(filtered_data)
            
            # Step 2: Extract and group data (limit group size for performance)
            if grouping_criteria and filtered_data:
                grouped_data = {}
                for item in filtered_data:
                    if isinstance(item, dict):
                        # Create group key based on grouping criteria
                        group_key_parts = []
                        for criterion in grouping_criteria:
                            if criterion in item:
                                group_key_parts.append(str(item[criterion]))
                            else:
                                # Try to find similar field names
                                found = False
                                for key in item.keys():
                                    if criterion.lower() in key.lower() or key.lower() in criterion.lower():
                                        group_key_parts.append(str(item[key]))
                                        found = True
                                        break
                                if not found:
                                    group_key_parts.append("Unknown")
                        group_key = " | ".join(group_key_parts)
                        
                        if group_key not in grouped_data:
                            grouped_data[group_key] = []
                        # Limit items per group to prevent memory issues
                        if len(grouped_data[group_key]) < 100:
                            grouped_data[group_key].append(item)
                
                results["patterns"]["grouped_data"] = grouped_data
                results["patterns"]["group_count"] = len(grouped_data)
                
                # Step 3: Apply aggregation methods
                if "count" in aggregation_methods:
                    results["statistics"]["group_counts"] = {
                        group: len(items) for group, items in grouped_data.items()
                    }
                
                if "percentage" in aggregation_methods:
                    total = len(filtered_data)
                    results["statistics"]["group_percentages"] = {
                        group: (len(items) / total * 100) if total > 0 else 0 
                        for group, items in grouped_data.items()
                    }
            
            # Step 4: Extract specific fields for analysis (limit field values for performance)
            if fields_to_extract and filtered_data:
                extracted_fields = {}
                for field in fields_to_extract:
                    field_values = []
                    for item in filtered_data:
                        if isinstance(item, dict) and field in item:
                            field_values.append(item[field])
                        elif isinstance(item, dict):
                            # Try to find similar field names
                            for key in item.keys():
                                if field.lower() in key.lower() or key.lower() in field.lower():
                                    field_values.append(item[key])
                                    break
                        # Limit field values to prevent memory issues
                        if len(field_values) >= 500:
                            break
                    extracted_fields[field] = field_values
                
                results["patterns"]["extracted_fields"] = extracted_fields
                
                # Calculate field statistics
                for field, values in extracted_fields.items():
                    if values:
                        # Count unique values
                        unique_values = list(set(values))
                        results["statistics"][f"{field}_unique_count"] = len(unique_values)
                        results["statistics"][f"{field}_total_count"] = len(values)
                        
                        # Most common values (limit to top 10)
                        value_counts = Counter(values)
                        results["statistics"][f"{field}_most_common"] = value_counts.most_common(10)
            
            # Step 5: Generate insights based on analysis type
            analysis_type = analysis_plan.get("analysis_type", "general")
            
            if analysis_type == "geographic_analysis":
                # Look for geographic patterns
                if "location" in results["patterns"].get("extracted_fields", {}):
                    locations = results["patterns"]["extracted_fields"]["location"]
                    results["insights"].append(f"Found {len(set(locations))} unique locations")
                
            elif analysis_type == "temporal_analysis":
                # Look for temporal patterns
                if "start_date" in results["patterns"].get("extracted_fields", {}):
                    dates = results["patterns"]["extracted_fields"]["start_date"]
                    results["insights"].append(f"Analyzed {len(dates)} trials across time")
                
            elif analysis_type == "sponsor_analysis":
                # Look for sponsor patterns
                if "sponsor" in results["patterns"].get("extracted_fields", {}):
                    sponsors = results["patterns"]["extracted_fields"]["sponsor"]
                    results["insights"].append(f"Found {len(set(sponsors))} unique sponsors")
            
            # General insights
            if filtered_data:
                results["insights"].append(f"Successfully analyzed {len(filtered_data)} data items")
                if results["patterns"].get("group_count", 0) > 0:
                    results["insights"].append(f"Data grouped into {results['patterns']['group_count']} categories")
            
            # CRITICAL FIX: Include raw data samples in analysis results with DYNAMIC truncation
            # This ensures downstream synthesis has access to actual data, not just summaries
            # Use SMART truncation to maximize content while staying within token limits
            if filtered_data and len(filtered_data) > 0:
                # Step 1: Prioritize diverse samples if grouped
                if results["patterns"].get("grouped_data"):
                    # Take samples from each group for diversity
                    sampled_data = []
                    grouped_data = results["patterns"]["grouped_data"]
                    # Start with generous allocation
                    items_per_group = max(1, 100 // len(grouped_data))
                    
                    for group_items in grouped_data.values():
                        sampled_data.extend(group_items[:items_per_group])
                        if len(sampled_data) >= 100:
                            break
                    raw_sample = sampled_data[:100]
                else:
                    # No grouping, take up to 100 items
                    raw_sample = filtered_data[:100]
                
                # Step 2: Estimate token usage and dynamically truncate
                # Average tokens per field (empirical estimates):
                # - nct_id: 5 tokens
                # - title: 50 tokens (full) / 25 tokens (truncated)
                # - condition: 10 tokens
                # - phase: 5 tokens
                # - status: 5 tokens
                # - sponsor: 10 tokens
                # - enrollment: 5 tokens
                # - dates: 10 tokens (both)
                # - brief_summary: 100 tokens (full) / 40 tokens (truncated)
                # - primary_endpoint: 40 tokens (truncated)
                # - intervention_type: 10 tokens
                # - locations: 20 tokens (5 items)
                
                # Estimate current token usage
                estimated_tokens_per_item = 0
                sample_item = raw_sample[0] if raw_sample else {}
                
                # Calculate based on what fields are actually present
                base_tokens = 80  # Core fields (nct_id, condition, phase, status, sponsor, enrollment, dates)
                
                # Check available fields and their estimated contribution
                has_title = "title" in sample_item
                has_summary = "brief_summary" in sample_item
                has_endpoint = "primary_endpoint" in sample_item
                has_intervention = "intervention_type" in sample_item
                has_locations = "locations" in sample_item or "countries" in sample_item
                
                # Target: ~15,000 tokens total for raw_data_sample (leaving room for analysis results)
                # This is ~7.5% of the 200K limit, which is reasonable
                target_token_budget = 15000
                
                # Calculate optimal strategy based on data size
                num_items = len(raw_sample)
                tokens_per_item_budget = target_token_budget // max(1, num_items)
                
                print(f"🎯 Token budget for {num_items} items: {target_token_budget:,} total, ~{tokens_per_item_budget} per item")
                
                # Adaptive truncation strategy based on available budget
                truncated_sample = []
                for item in raw_sample:
                    if isinstance(item, dict):
                        # Always include core fields
                        truncated_item = {
                            "nct_id": item.get("nct_id", ""),
                            "condition": item.get("condition", ""),
                            "phase": item.get("phase", ""),
                            "status": item.get("status", ""),
                            "sponsor": item.get("sponsor", ""),
                            "enrollment": item.get("enrollment", item.get("enrollment_count", "")),
                            "start_date": item.get("start_date", ""),
                            "completion_date": item.get("completion_date", "")
                        }
                        
                        # Adaptive field inclusion based on token budget
                        if tokens_per_item_budget >= 200:
                            # Generous budget - include more fields with less truncation
                            truncated_item["title"] = (item.get("title", "") or "")[:400]
                            if "brief_summary" in item and item["brief_summary"]:
                                truncated_item["brief_summary"] = (item["brief_summary"] or "")[:600]
                            if "primary_endpoint" in item:
                                truncated_item["primary_endpoint"] = (item.get("primary_endpoint", "") or "")[:400]
                            if "intervention_type" in item:
                                truncated_item["intervention_type"] = item.get("intervention_type", "")
                            if "study_type" in item:
                                truncated_item["study_type"] = item.get("study_type", "")
                            if "locations" in item and isinstance(item["locations"], list):
                                truncated_item["locations"] = item["locations"][:8]
                            elif "countries" in item:
                                truncated_item["countries"] = item.get("countries", "")
                        
                        elif tokens_per_item_budget >= 120:
                            # Moderate budget - balanced approach
                            truncated_item["title"] = (item.get("title", "") or "")[:300]
                            if "brief_summary" in item and item["brief_summary"]:
                                truncated_item["brief_summary"] = (item["brief_summary"] or "")[:400]
                            if "primary_endpoint" in item:
                                truncated_item["primary_endpoint"] = (item.get("primary_endpoint", "") or "")[:250]
                            if "intervention_type" in item:
                                truncated_item["intervention_type"] = item.get("intervention_type", "")
                            if "locations" in item and isinstance(item["locations"], list):
                                truncated_item["locations"] = item["locations"][:5]
                            elif "countries" in item:
                                truncated_item["countries"] = item.get("countries", "")
                        
                        else:
                            # Tight budget - minimal approach
                            truncated_item["title"] = (item.get("title", "") or "")[:200]
                            if "brief_summary" in item and item["brief_summary"]:
                                truncated_item["brief_summary"] = (item["brief_summary"] or "")[:250]
                            if "primary_endpoint" in item:
                                truncated_item["primary_endpoint"] = (item.get("primary_endpoint", "") or "")[:150]
                        
                        truncated_sample.append(truncated_item)
                    else:
                        truncated_sample.append(item)
                
                results["raw_data_sample"] = truncated_sample
                
                # Estimate actual tokens used
                estimated_total_tokens = len(truncated_sample) * tokens_per_item_budget
                results["insights"].append(
                    f"Included {len(truncated_sample)} raw data samples for synthesis "
                    f"(~{estimated_total_tokens:,} tokens, dynamic truncation)"
                )
                print(f"📋 Including {len(truncated_sample)} raw data items in analysis results")
                print(f"💡 Estimated token usage: ~{estimated_total_tokens:,} tokens (~{tokens_per_item_budget} per item)")
            
            return results
            
        except Exception as e:
            print(f"❌ Error in data analysis: {e}")
            return {
                "error": str(e),
                "analysis_type": analysis_plan.get("analysis_type", "general"),
                "insights": ["Error occurred during data analysis"]
            }

    def _matches_criteria(self, item: Dict, field: str, value: str) -> bool:
        """Check if an item matches the given field criteria with support for operators and special fields"""
        try:
            # Handle special sorting fields
            if field == "sort_by":
                # This is a sorting instruction, not a filtering criteria
                return True
            
            if field == "order":
                # This is a sorting instruction, not a filtering criteria
                return True
            
            # Find the actual field in the item (with fuzzy matching)
            actual_field = None
            actual_value = None
            
            # Direct field match
            if field in item:
                actual_field = field
                actual_value = item[field]
            else:
                # Fuzzy field matching
                for key in item.keys():
                    if field.lower() in key.lower() or key.lower() in field.lower():
                        actual_field = key
                        actual_value = item[key]
                        break
            
            if actual_field is None or actual_value is None:
                return False
            
            # Handle different value types and operators
            if isinstance(value, str):
                # Check for operators
                if value.startswith(">"):
                    # Greater than
                    try:
                        threshold = float(value[1:])
                        item_value = float(actual_value) if actual_value else 0
                        return item_value > threshold
                    except (ValueError, TypeError):
                        return False
                elif value.startswith("<"):
                    # Less than
                    try:
                        threshold = float(value[1:])
                        item_value = float(actual_value) if actual_value else 0
                        return item_value < threshold
                    except (ValueError, TypeError):
                        return False
                elif value.startswith(">="):
                    # Greater than or equal
                    try:
                        threshold = float(value[2:])
                        item_value = float(actual_value) if actual_value else 0
                        return item_value >= threshold
                    except (ValueError, TypeError):
                        return False
                elif value.startswith("<="):
                    # Less than or equal
                    try:
                        threshold = float(value[2:])
                        item_value = float(actual_value) if actual_value else 0
                        return item_value <= threshold
                    except (ValueError, TypeError):
                        return False
                elif value.startswith("!="):
                    # Not equal
                    return str(actual_value).lower() != value[2:].lower()
                elif value.startswith("="):
                    # Exact match
                    return str(actual_value).lower() == value[1:].lower()
                else:
                    # Contains match (default)
                    if isinstance(actual_value, str):
                        return value.lower() in actual_value.lower()
                    else:
                        return str(actual_value).lower() == value.lower()
            else:
                # Direct value comparison
                return actual_value == value
                
        except Exception as e:
            print(f"❌ Error in criteria matching: {e}")
            return False

    async def _execute_data_filtering(self, data: Any, filter_plan: Dict) -> Dict:
        """Execute data filtering based on LLM-provided instructions"""
        try:

            results = {
                "filter_type": filter_plan.get("filter_type", "simple"),
                "filtering_criteria": filter_plan.get("filtering_criteria", {}),
                "filtered_data": [],
                "summary": {},
                "insights": []
            }
            
            # Convert data to list if it's not already
            if not isinstance(data, list):
                data = [data] if data else []
            
            if not data:
                results["insights"].append("No data available for filtering")
                return results
            
            # Extract parameters
            filtering_criteria = filter_plan.get("filtering_criteria", {})
            sorting_criteria = filter_plan.get("sorting_criteria", [])
            limit = filter_plan.get("limit", 10)
            filtering_logic = filter_plan.get("filtering_logic", "AND")
            special_conditions = filter_plan.get("special_conditions", [])
            
            results["summary"]["total_items"] = len(data)
            
            # Step 1: Apply filtering criteria
            filtered_data = data
            if filtering_criteria:
                # Handle string criteria by using LLM to parse it intelligently
                if isinstance(filtering_criteria, str):
                    
                    # Ensure we have sample data for the LLM prompt
                    sample_data = data[0] if data and isinstance(data, list) and len(data) > 0 else {}
                    
                    # Use LLM to parse the string criteria into proper filtering parameters
                    criteria_parsing_prompt = f"""
You are an expert data filtering assistant. Parse the following filter criteria string into specific filtering parameters.

FILTER CRITERIA: {filtering_criteria}

SAMPLE DATA STRUCTURE: {json.dumps(sample_data, indent=2)}

INSTRUCTIONS:
1. Analyze the filter criteria string and determine what filtering/sorting is needed
2. Convert it into a proper filtering_criteria dictionary
3. Consider common patterns like:
   - "most recent" → sort by date in descending order
   - "largest/smallest" → sort by size/number in ascending/descending order
   - "phase 3" → filter by phase
   - "active/recruiting" → filter by status
   - "diabetes/cancer" → filter by condition
   - "Eli Lilly/Novo Nordisk" → filter by sponsor

Return ONLY valid JSON with filtering parameters:

{{
    "filtering_criteria": {{"field": "value", "field2": "value2"}},
    "sorting_criteria": ["field1", "field2"],
    "sort_by": "field_name",
    "sort_order": "asc|desc",
    "limit": 10
}}

EXAMPLES:
- "most_recent_start_date" → {{"sort_by": "start_date", "sort_order": "desc"}}
- "largest_enrollment" → {{"sort_by": "enrollment", "sort_order": "desc"}}
- "smallest_trial" → {{"sort_by": "enrollment", "sort_order": "asc"}}
- "phase_3_trials" → {{"filtering_criteria": {{"phase": "phase"}}, "sort_by": "start_date", "sort_order": "desc"}}
- "active_diabetes_trials" → {{"filtering_criteria": {{"status": "active", "condition": "diabetes"}}, "sort_by": "start_date", "sort_order": "desc"}}

JSON Response:
"""
                    
                    try:
                        import re
                        
                        # Get LLM response
                        llm_response = await llm_agent.generate_structured_response(
                            criteria_parsing_prompt,
                            system_prompt="You are an expert data filtering assistant. Parse filter criteria into structured parameters."
                        )
                        
                        # Clean and parse the response
                        cleaned_response = re.sub(r'```json\s*', '', llm_response)
                        cleaned_response = re.sub(r'```\s*$', '', cleaned_response)
                        cleaned_response = re.sub(r'```\s*', '', cleaned_response)
                        
                        parsed_criteria = json.loads(cleaned_response)
                        
                        # Update the filtering_criteria with parsed values
                        if "filtering_criteria" in parsed_criteria:
                            filtering_criteria = parsed_criteria["filtering_criteria"]
                        if "sort_by" in parsed_criteria:
                            sorting_criteria = [parsed_criteria["sort_by"]] + sorting_criteria
                        if "sort_order" in parsed_criteria:
                            # Store sort order for later use
                            sort_order = parsed_criteria["sort_order"]
                        if "limit" in parsed_criteria:
                            limit = parsed_criteria["limit"]
                            
                        # If we have sort_by in the parsed criteria, add it to filtering_criteria for sorting
                        if "sort_by" in parsed_criteria:
                            if not isinstance(filtering_criteria, dict):
                                filtering_criteria = {}
                            filtering_criteria["sort_by"] = parsed_criteria["sort_by"]
                            filtering_criteria["sort_order"] = parsed_criteria.get("sort_order", "desc")
                        
                    except Exception as e:
                        print(f"❌ Error parsing criteria with LLM: {e}")
                        # Fallback to simple sorting by the field mentioned
                        if "smallest" in filtering_criteria.lower():
                            filtering_criteria = {"sort_by": "enrollment", "sort_order": "asc"}
                        elif "largest" in filtering_criteria.lower():
                            filtering_criteria = {"sort_by": "enrollment", "sort_order": "desc"}
                        elif "recent" in filtering_criteria.lower():
                            filtering_criteria = {"sort_by": "start_date", "sort_order": "desc"}
                        else:
                            filtering_criteria = {"sort_by": filtering_criteria, "sort_order": "desc"}
                
                # Ensure filtering_criteria is a dictionary
                if not isinstance(filtering_criteria, dict):
                    print(f"⚠️ Invalid filtering criteria type: {type(filtering_criteria)}")
                    filtering_criteria = {}
                
                if filtering_criteria:
                    filtered_data = []
                    for item in data:
                        if isinstance(item, dict):
                            include_item = True
                            
                            if filtering_logic == "AND":
                                # All criteria must match
                                for field, value in filtering_criteria.items():
                                    if not self._matches_criteria(item, field, value):
                                        include_item = False
                                        break
                            else:  # OR logic
                                # At least one criteria must match
                                any_match = False
                                for field, value in filtering_criteria.items():
                                    if self._matches_criteria(item, field, value):
                                        any_match = True
                                        break
                                include_item = any_match
                            
                            if include_item:
                                filtered_data.append(item)
            
            # Step 2: Apply special conditions
            if special_conditions and filtered_data:
                for condition in special_conditions:
                    condition_lower = condition.lower()
                    if "active" in condition_lower or "recruiting" in condition_lower:
                        # Filter for active/recruiting trials
                        filtered_data = [
                            item for item in filtered_data 
                            if isinstance(item, dict) and (
                                "status" in item and any(status in str(item["status"]).lower() 
                                                       for status in ["active", "recruiting", "ongoing"])
                            )
                        ]
                    elif "recent" in condition_lower:
                        # Filter for recent trials (last 2 years)
                        cutoff_date = datetime.now() - timedelta(days=730)
                        filtered_data = [
                            item for item in filtered_data 
                            if isinstance(item, dict) and (
                                "start_date" not in item or 
                                (item["start_date"] and item["start_date"] > cutoff_date.strftime("%Y-%m-%d"))
                            )
                        ]
                    elif "large" in condition_lower or "enrollment" in condition_lower:
                        # Filter for large trials
                        filtered_data = [
                            item for item in filtered_data 
                            if isinstance(item, dict) and (
                                "enrollment" not in item or 
                                (item["enrollment"] and item["enrollment"] > 100)
                            )
                        ]
                    elif "phase3" in condition_lower or "phase 3" in condition_lower:
                        # Filter for Phase 3 trials
                        filtered_data = [
                            item for item in filtered_data 
                            if isinstance(item, dict) and (
                                "phase" in item and "phase3" in str(item["phase"]).lower()
                            )
                        ]
                    elif "completed" in condition_lower:
                        # Filter for completed trials
                        filtered_data = [
                            item for item in filtered_data 
                            if isinstance(item, dict) and (
                                "status" in item and "completed" in str(item["status"]).lower()
                            )
                        ]
                    elif "diabetes" in condition_lower:
                        # Filter for diabetes trials
                        filtered_data = [
                            item for item in filtered_data 
                            if isinstance(item, dict) and (
                                "condition" in item and "diabetes" in str(item["condition"]).lower()
                            )
                        ]
                    elif "lilly" in condition_lower or "eli" in condition_lower:
                        # Filter for Eli Lilly trials
                        filtered_data = [
                            item for item in filtered_data 
                            if isinstance(item, dict) and (
                                "sponsor" in item and "lilly" in str(item["sponsor"]).lower()
                            )
                        ]
            
            # Step 3: Apply sorting
            if sorting_criteria and filtered_data:
                def sort_key(item):
                    if not isinstance(item, dict):
                        return ""
                    key_parts = []
                    for criterion in sorting_criteria:
                        if criterion in item:
                            key_parts.append(str(item[criterion]))
                        else:
                            key_parts.append("")
                    return " | ".join(key_parts)
                
                filtered_data.sort(key=sort_key)
            
            # Also check for sorting criteria in the filtering_criteria
            if isinstance(filtering_criteria, dict) and filtering_criteria.get("sort_by"):
                sort_field = filtering_criteria.get("sort_by")
                sort_order = filtering_criteria.get("sort_order", "desc")
                
                print(f"📊 Applying sorting: {sort_field} in {sort_order} order")
                
                def sort_key(item):
                    if not isinstance(item, dict):
                        return ""
                    if sort_field in item:
                        value = item[sort_field]
                        # Handle date sorting
                        if isinstance(value, str) and "-" in value:
                            try:
                                return datetime.strptime(value, "%Y-%m-%d")
                            except:
                                return value
                        # Handle numeric sorting
                        try:
                            return float(value) if value else 0
                        except:
                            return str(value) if value else ""
                    return ""
                
                filtered_data.sort(key=sort_key, reverse=(sort_order.lower() == "desc"))
            
            # Step 4: Apply limit
            if limit > 0 and len(filtered_data) > limit:
                filtered_data = filtered_data[:limit]
            
            # Create results structure
            results = {
                "filter_type": filter_plan.get("filter_type", "simple"),
                "filtering_criteria": filtering_criteria,
                "filtered_data": filtered_data,
                "summary": {
                    "total_items": len(data),
                    "filtered_items": len(filtered_data),
                    "reduction_percentage": (
                        (len(data) - len(filtered_data)) / len(data) * 100 if len(data) > 0 else 0
                    )
                },
                "insights": []
            }
            
            # Step 5: Generate insights
            results["insights"].append(f"Filtered {len(data)} items to {len(filtered_data)} items")
            if filtering_criteria:
                results["insights"].append(f"Applied {len(filtering_criteria)} filtering criteria")
            if special_conditions:
                results["insights"].append(f"Applied {len(special_conditions)} special conditions")
            if sorting_criteria:
                results["insights"].append(f"Sorted by {', '.join(sorting_criteria)}")
            
            return results
            
        except Exception as e:
            print(f"❌ Error in data filtering: {e}")
            return {
                "error": str(e),
                "filter_type": filter_plan.get("filter_type", "simple"),
                "filtered_data": data if isinstance(data, list) else [data],
                "insights": ["Error occurred during data filtering"]
            }

    async def _execute_data_extraction(self, data: Any, extraction_plan: Dict) -> Dict:
        """Execute data extraction based on LLM-provided instructions"""
        try:
            results = {
                "extraction_type": extraction_plan.get("extraction_type", "general"),
                "target_fields": extraction_plan.get("target_fields", []),
                "extracted_data": {},
                "summary": {},
                "insights": []
            }
            
            # Convert data to list if it's not already
            if not isinstance(data, list):
                data = [data] if data else []
            
            if not data:
                results["insights"].append("No data available for extraction")
                return results
            
            # Extract parameters
            target_fields = extraction_plan.get("target_fields", [])
            filtering_criteria = extraction_plan.get("filtering_criteria", {})
            grouping_criteria = extraction_plan.get("grouping_criteria", [])
            
            # Step 1: Filter data based on criteria
            filtered_data = data
            if filtering_criteria:
                filtered_data = []
                for item in data:
                    if isinstance(item, dict):
                        include_item = True
                        for field, value in filtering_criteria.items():
                            if field in item and item[field] != value:
                                include_item = False
                                break
                        if include_item:
                            filtered_data.append(item)
            
            results["summary"]["total_items"] = len(data)
            results["summary"]["filtered_items"] = len(filtered_data)
            
            # Step 2: Extract target fields
            if target_fields and filtered_data:
                extracted_fields = {}
                for field in target_fields:
                    field_values = []
                    for item in filtered_data:
                        if isinstance(item, dict) and field in item:
                            field_values.append(item[field])
                        elif isinstance(item, dict):
                            # Try to find similar field names
                            for key in item.keys():
                                if field.lower() in key.lower() or key.lower() in field.lower():
                                    field_values.append(item[key])
                                    break
                    extracted_fields[field] = field_values
                
                results["extracted_data"]["fields"] = extracted_fields
                
                # Step 3: Group data if requested
                if grouping_criteria and filtered_data:
                    grouped_data = {}
                    for item in filtered_data:
                        if isinstance(item, dict):
                            # Create group key based on grouping criteria
                            group_key_parts = []
                            for criterion in grouping_criteria:
                                if criterion in item:
                                    group_key_parts.append(str(item[criterion]))
                                else:
                                    # Try to find similar field names
                                    found = False
                                    for key in item.keys():
                                        if criterion.lower() in key.lower() or key.lower() in criterion.lower():
                                            group_key_parts.append(str(item[key]))
                                            found = True
                                            break
                                    if not found:
                                        group_key_parts.append("Unknown")
                            group_key = " | ".join(group_key_parts)
                            
                            if group_key not in grouped_data:
                                grouped_data[group_key] = []
                            grouped_data[group_key].append(item)
                    
                    results["extracted_data"]["grouped_data"] = grouped_data
                    results["summary"]["group_count"] = len(grouped_data)
                
                # Step 4: Generate insights
                for field, values in extracted_fields.items():
                    if values:
                        unique_values = list(set(values))
                        results["insights"].append(f"Extracted {len(values)} values for '{field}' ({len(unique_values)} unique)")
                        
                        # Most common values
                        value_counts = Counter(values)
                        results["extracted_data"][f"{field}_most_common"] = value_counts.most_common(5)
            
            # Step 5: Handle specific extraction types
            extraction_type = extraction_plan.get("extraction_type", "general")
            
            if extraction_type == "site_extraction":
                # Look for site-related fields
                site_fields = ["facility_name", "location", "city", "state", "country"]
                for field in site_fields:
                    if field in results["extracted_data"].get("fields", {}):
                        values = results["extracted_data"]["fields"][field]
                        results["insights"].append(f"Found {len(set(values))} unique {field} values")
            
            elif extraction_type == "trial_extraction":
                # Look for trial-related fields
                trial_fields = ["phase", "status", "enrollment", "start_date"]
                for field in trial_fields:
                    if field in results["extracted_data"].get("fields", {}):
                        values = results["extracted_data"]["fields"][field]
                        results["insights"].append(f"Extracted {len(values)} {field} values")
            
            # General insights
            if filtered_data:
                results["insights"].append(f"Successfully extracted data from {len(filtered_data)} items")
            
            return results
            
        except Exception as e:
            print(f"❌ Error in data extraction: {e}")
            return {
                "error": str(e),
                "extraction_type": extraction_plan.get("extraction_type", "general"),
                "insights": ["Error occurred during data extraction"]
            }

    async def process_dynamic_query(self, query: str, include_graph_plan: bool = False, conversation_history: List[Dict] = None, progress_callback=None, study_context: Dict = None, selected_trials: List = None, regulatory_documents: List[Dict] = None, selected_agents: List[str] = None, deep_research: Optional[bool] = None) -> DynamicQueryResponse:
        """Process a query using dynamic graph construction
        
        Args:
            query: The user's query
            include_graph_plan: Whether to include the graph plan in the response
            conversation_history: Previous conversation context
            progress_callback: Callback for progress updates
            study_context: Study design context (phase, indication, drug name, etc.)
            selected_trials: List of selected reference trials
            regulatory_documents: Uploaded document payloads with extracted_text (Regulatory Intelligence)
            selected_agents: Optional agent ids from UI to bias planning
            deep_research: When True/False, overrides settings.DEEP_RESEARCH_ENABLED for this request.
        """
        start_time = asyncio.get_event_loop().time()
        regulatory_documents = regulatory_documents or []
        selected_agents = selected_agents or []
        dr_enabled = settings.DEEP_RESEARCH_ENABLED if deep_research is None else bool(deep_research)
        run_id = str(uuid.uuid4())
        seq_counter = [0]
        _raw_progress = progress_callback
        _progress_cb_lock = asyncio.Lock()

        async def _locked_progress(data: Any) -> None:
            if _raw_progress:
                async with _progress_cb_lock:
                    await _raw_progress(data)

        progress_callback = _locked_progress if _raw_progress else None

        async def deep_emit(ws_type: str, phase: str, data: Dict[str, Any]) -> None:
            if not progress_callback:
                return
            seq_counter[0] += 1
            payload = {
                "type": ws_type,
                "run_id": run_id,
                "seq": seq_counter[0],
                "phase": phase,
                "timestamp": datetime.now().isoformat(),
                "data": data,
            }
            try:
                await progress_callback(payload)
            except Exception as e:
                print(f"⚠️ deep_emit failed: {e}")
        
        try:
            # Log the query
            log_query(f"Dynamic query: {query}")
            
            effective_query = query
            if regulatory_documents:
                reg_blob = _format_regulatory_documents_for_query(regulatory_documents)
                effective_query = (
                    f"{query}\n\n---\nREGULATORY DOCUMENT CONTEXT (user uploads; cite and ground answers here when relevant):\n"
                    f"{reg_blob}\n---"
                )

            # Check cache first
            conversation_hash = hash(str(conversation_history)) if conversation_history else 0
            reg_hash = hash(str(regulatory_documents)) if regulatory_documents else 0
            ag_hash = hash(tuple(selected_agents)) if selected_agents else 0
            cache_key = f"dynamic_query:{hash(query)}_{conversation_hash}_{reg_hash}_{ag_hash}_{int(dr_enabled)}"
            cached_response = cache_manager.get(cache_key)
            
            if cached_response:
                return cached_response
            
            # Step 1: Assess query and create graph plan
            print(f"🔍 Assessing query and planning graph for: {query}")
            
            # Send progress update for query analysis start
            if progress_callback:
                analysis_start_data = {
                    "node_id": "query_analysis",
                    "node_type": "analysis",
                    "status": "started",
                    "start_time": datetime.now().isoformat(),
                    "end_time": None,
                    "description": "Analyzing query and creating execution plan",
                    "error": ""
                }
                try:
                    await progress_callback(analysis_start_data)
                    print(f"✅ Query analysis start progress sent")
                except Exception as e:
                    print(f"⚠️ Error sending query analysis start progress: {e}")

            research_spec: Optional[Dict[str, Any]] = None
            if dr_enabled:
                try:
                    research_spec = await build_research_brief_and_outline(effective_query)
                    brief_data = {
                        "brief": research_spec.get("brief", ""),
                        "assumptions": research_spec.get("assumptions", []),
                        "must_have_facts": research_spec.get("must_have_facts", []),
                    }
                    brief_data.update(ui_brief_payload(research_spec))
                    await deep_emit("research_brief_ready", "brief", brief_data)
                    outline_list = research_spec.get("outline") or []
                    outline_data: Dict[str, Any] = {"outline": outline_list}
                    outline_data.update(ui_outline_payload(outline_list))
                    await deep_emit("research_outline_ready", "plan", outline_data)
                except Exception as e:
                    log_error(e, "deep_research brief/outline")
                    research_spec = None
            
            graph_plan = await self.assess_query_and_plan_graph(
                effective_query,
                conversation_history,
                study_context=study_context,
                selected_trials=selected_trials,
                selected_agents=selected_agents,
                research_spec=research_spec,
                deep_plan=dr_enabled,
            )
            print(f"✅ Graph plan created with {len(graph_plan.nodes)} nodes")
            
            # Send progress update for query analysis completion AND graph plan ready
            if progress_callback:
                # First, send the graph_plan_ready message (special type for WebSocket handler)
                graph_plan_ready_data = {
                    "type": "graph_plan_ready",
                    "graph_plan": graph_plan.dict()
                }
                try:
                    await progress_callback(graph_plan_ready_data)
                    print(f"✅ Graph plan ready signal sent to frontend")
                except Exception as e:
                    print(f"⚠️ Error sending graph plan ready signal: {e}")

                if dr_enabled:
                    eo = graph_plan.execution_order or []
                    preview = " → ".join(eo[:15]) + (" → …" if len(eo) > 15 else "")
                    reasoning_txt = (graph_plan.reasoning or "").strip() or "No separate planner commentary returned."
                    planner_lines = [
                        f"Planner chose {len(graph_plan.nodes)} steps with {len(graph_plan.edges)} dependency edge(s).",
                        "Execution order preview: " + preview,
                    ]
                    await deep_emit(
                        "deep_research_phase",
                        "planner",
                        {
                            "message": "Mapped outline + brief to an executable graph.",
                            "thinking_lines": planner_lines,
                            "planner_reasoning": reasoning_txt[:2200],
                            "execution_order_preview": preview,
                            "node_summary": [
                                {
                                    "id": n.id,
                                    "type": n.type,
                                    "description": (n.description or "")[:200],
                                }
                                for n in graph_plan.nodes[:20]
                            ],
                            "extra_nodes_omitted": max(0, len(graph_plan.nodes) - 20),
                        },
                    )
                
                # Then send the regular analysis completion progress
                reasoning_snip = (graph_plan.reasoning or "")[:280].replace("\n", " ")
                analysis_desc = (
                    f"Graph ready: {len(graph_plan.nodes)} nodes. "
                    f"{reasoning_snip}{'…' if len(graph_plan.reasoning or '') > 280 else ''}"
                )
                analysis_complete_data = {
                    "node_id": "query_analysis",
                    "node_type": "analysis",
                    "status": "completed",
                    "start_time": analysis_start_data["start_time"] if 'analysis_start_data' in locals() else datetime.now().isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "description": analysis_desc,
                    "error": ""
                }
                try:
                    await progress_callback(analysis_complete_data)
                    print(f"✅ Query analysis complete progress sent")
                except Exception as e:
                    print(f"⚠️ Error sending query analysis complete progress: {e}")
            
            # Log detailed graph plan structure
            print("\n📊 GRAPH PLAN DETAILS:")
            print("=" * 60)
            print(f"REASONING: {graph_plan.reasoning}")
            print(f"EXECUTION ORDER: {' → '.join(graph_plan.execution_order)}")
            print(f"TOTAL EDGES: {len(graph_plan.edges)}")
            print("\nNODES:")
            print("-" * 40)
            for i, node in enumerate(graph_plan.nodes, 1):
                print(f"{i}. {node.id} ({node.type})")
                print(f"   Description: {node.description}")
                print(f"   Parameters: {node.parameters}")
                print(f"   Dependencies: {node.dependencies}")
                print()
            
            print("EDGES:")
            print("-" * 40)
            for i, edge in enumerate(graph_plan.edges, 1):
                print(f"{i}. {edge['from']} → {edge['to']}")
            print("=" * 60)
            
            # Step 2: Context manager, optional parallel prefetch, execute (+ deep replan loop)
            context_manager = ContextManager(query=effective_query)
            await self._seed_context_manager(
                context_manager,
                effective_query,
                conversation_history=conversation_history,
                study_context=study_context,
                selected_trials=selected_trials,
                research_spec=research_spec,
                run_id=run_id,
            )
            if study_context:
                print(f"✅ Added study context to context manager: {study_context.get('phase')} {study_context.get('indication')} {study_context.get('drugName')}")
            if selected_trials:
                print(f"✅ Added {len(selected_trials)} selected trials to context manager")

            incremental_dr: Optional[Dict[str, Any]] = None
            if dr_enabled and research_spec and settings.DEEP_RESEARCH_INCREMENTAL:
                incremental_dr = {
                    "enabled": True,
                    "research_spec": research_spec,
                    "emit": deep_emit,
                }

            parallel_subruns_merged = 0
            parallel_lines: List[str] = []
            use_parallel = False
            if dr_enabled and research_spec and settings.DEEP_RESEARCH_PARALLEL_SUBRUNS:
                use_parallel, parallel_lines = broad_query_explanation(
                    effective_query, research_spec
                )
            if use_parallel:
                n_branches = max(
                    2, min(int(settings.DEEP_RESEARCH_PARALLEL_BRANCH_COUNT), 8)
                )
                outline_full = research_spec.get("outline") or []
                chunks = self._split_outline_into_chunks(outline_full, n_branches)
                if len(chunks) >= 2:
                    branch_summaries: List[str] = []
                    for i, ch in enumerate(chunks[:6]):
                        focus = ", ".join(str(s.get("title") or "") for s in ch[:4])
                        branch_summaries.append(
                            f"Branch {i + 1}: {focus or f'{len(ch)} outline section(s)'}"
                        )
                    await deep_emit(
                        "deep_research_phase",
                        "parallel_merge",
                        {
                            "message": f"Running {len(chunks)} parallel sub-research branches, then merging results.",
                            "thinking_lines": parallel_lines + branch_summaries,
                        },
                    )

                    async def _parallel_branch(tag: str, half: List[Dict[str, Any]]) -> ContextManager:
                        spec_half = {
                            **research_spec,
                            "outline": half,
                        }
                        focus = ", ".join(str(s.get("title") or "") for s in half[:6])
                        sub_q = f"{effective_query}\n\n(Sub-research focus: {focus})"
                        cm_sub = ContextManager(query=effective_query)
                        await self._seed_context_manager(
                            cm_sub,
                            effective_query,
                            conversation_history=conversation_history,
                            study_context=study_context,
                            selected_trials=selected_trials,
                            research_spec=spec_half,
                            run_id=run_id,
                        )
                        plan_sub = self._partition_graph_plan_for_outline_sections(
                            graph_plan, half
                        )
                        if plan_sub is None:
                            plan_sub = await self.assess_query_and_plan_graph(
                                sub_q,
                                conversation_history,
                                study_context=study_context,
                                selected_trials=selected_trials,
                                selected_agents=selected_agents,
                                research_spec=spec_half,
                                deep_plan=True,
                            )
                        sub_incremental = None
                        if dr_enabled and research_spec and settings.DEEP_RESEARCH_INCREMENTAL:
                            sub_incremental = {
                                "enabled": True,
                                "research_spec": spec_half,
                                "emit": deep_emit,
                            }
                        await self._run_graph_to_final_state(
                            plan_sub,
                            effective_query,
                            cm_sub,
                            progress_callback,
                            seed_execution_results=None,
                            incremental_dr=sub_incremental,
                            sanitize_deep_plan=True,
                        )
                        return cm_sub

                    cms = await asyncio.gather(
                        *[
                            _parallel_branch(f"sr{i}", ch)
                            for i, ch in enumerate(chunks)
                        ]
                    )
                    for i, cm_sub in enumerate(cms):
                        self._merge_context_manager_from(context_manager, cm_sub, f"sr{i}")
                    parallel_subruns_merged = len(cms)
                    await deep_emit(
                        "subruns_merged",
                        "parallel_merge",
                        {
                            "parallel_subruns_merged": parallel_subruns_merged,
                            "thinking_lines": [
                                f"All {parallel_subruns_merged} branches finished; merging context managers so synthesis sees one combined evidence pool.",
                                "Artifacts, execution summaries, and citation lists from parallel sub-runs are folded together before the main synthesize step.",
                            ],
                        },
                    )

            if incremental_dr:
                context_manager.global_context.setdefault("deep_research_working_answer", "")
                context_manager.global_context.pop("deep_research_skip_searches", None)
                context_manager.global_context.pop("deep_research_skip_reason", None)
                context_manager.global_context["deep_research_reflections"] = []
                await deep_emit(
                    "deep_research_phase",
                    "incremental",
                    {
                        "message": "Incremental deep research: after each search/analyze/extract step I'll judge source usefulness, update a running answer draft, and only skip later searches if evidence is clearly noise.",
                        "thinking_lines": [
                            "Running answer is refined step-by-step (not only at final synthesize).",
                            "Final synthesis still sees full context; the draft is a guide, not a replacement for evidence.",
                        ],
                    },
                )

            if progress_callback:
                execution_start_data = {
                    "node_id": "graph_execution",
                    "node_type": "execution",
                    "status": "started",
                    "start_time": datetime.now().isoformat(),
                    "end_time": None,
                    "description": (
                        f"Executing {len(graph_plan.nodes)} planned nodes in dependency order "
                        f"(parallel branches already merged: {parallel_subruns_merged})."
                    ),
                    "error": ""
                }
                try:
                    await progress_callback(execution_start_data)
                    print(f"✅ Graph execution start progress sent")
                except Exception as e:
                    print(f"⚠️ Error sending graph execution start progress: {e}")
            else:
                execution_start_data = {"start_time": datetime.now().isoformat()}

            execution_results: Dict[str, Any] = {}
            replan_round = 0
            verifier_passed: Optional[bool] = None
            final_state: Dict[str, Any] = {}

            while True:
                final_state = await self._run_graph_to_final_state(
                    graph_plan,
                    effective_query,
                    context_manager,
                    progress_callback,
                    seed_execution_results=execution_results,
                    incremental_dr=incremental_dr,
                    sanitize_deep_plan=dr_enabled,
                )
                execution_results = final_state.get("execution_results") or {}
                context_manager = final_state.get("context_manager") or context_manager

                if not dr_enabled or not research_spec:
                    break

                summary = summarize_execution_for_verifier(execution_results)
                try:
                    verdict = await verify_research_coverage(effective_query, research_spec, summary)
                except Exception as ver_err:
                    log_error(ver_err, "deep_research verifier")
                    verifier_passed = None
                    break
                verifier_passed = bool(verdict.get("passed"))
                if isinstance(context_manager.global_context, dict):
                    context_manager.global_context.setdefault("deep_research_trace", []).append(
                        {"verifier": verdict, "round": replan_round}
                    )

                verdict_payload = dict(verdict)
                verdict_payload.update(ui_verifier_payload(verdict))
                await deep_emit("verifier_result", "verify", verdict_payload)

                if verdict.get("passed") or replan_round >= settings.DEEP_RESEARCH_MAX_REPLANS:
                    break

                existing_ids = [n.id for n in graph_plan.nodes]
                gaps_list = list(verdict.get("gaps") or [])
                raw_nodes: List[Dict[str, Any]] = []
                raw_edges: List[Dict[str, str]] = []
                if settings.DEEP_RESEARCH_REPLAN_TARGETED and gaps_list:
                    raw_nodes, raw_edges = await replan_targeted_nodes_and_edges(
                        effective_query,
                        research_spec,
                        gaps_list,
                        existing_ids,
                        replan_round + 1,
                    )
                if not raw_nodes:
                    raw_nodes, raw_edges = await replan_new_nodes_json(
                        effective_query,
                        research_spec,
                        gaps_list,
                        existing_ids,
                    )
                if not raw_nodes:
                    break
                new_graph_nodes: List[GraphNode] = []
                for rn in raw_nodes[: settings.DEEP_RESEARCH_MAX_NEW_NODES_PER_ROUND]:
                    if not isinstance(rn, dict) or not rn.get("id"):
                        continue
                    new_graph_nodes.append(
                        GraphNode(
                            id=str(rn["id"]),
                            type=str(rn.get("type") or "search"),
                            description=str(rn.get("description") or ""),
                            parameters=rn.get("parameters") or {},
                            dependencies=list(rn.get("dependencies") or []),
                        )
                    )
                if not new_graph_nodes:
                    break
                graph_plan = merge_replan_into_plan(graph_plan, new_graph_nodes, raw_edges)
                graph_plan = self._sanitize_dynamic_chat_plan(graph_plan, deep_plan=True)
                if incremental_dr:
                    context_manager.global_context.pop("deep_research_skip_searches", None)
                    context_manager.global_context.pop("deep_research_skip_reason", None)
                replan_round += 1
                replan_data: Dict[str, Any] = {
                    "new_node_ids": [n.id for n in new_graph_nodes],
                    "round": replan_round,
                    "max_rounds": settings.DEEP_RESEARCH_MAX_REPLANS,
                    "graph_plan": graph_plan.dict(),
                }
                replan_data.update(
                    ui_replan_started_payload(
                        list(verdict.get("gaps") or []),
                        new_graph_nodes,
                    )
                )
                await deep_emit("replan_started", "replan", replan_data)

            if progress_callback:
                execution_complete_data = {
                    "node_id": "graph_execution",
                    "node_type": "execution",
                    "status": "completed",
                    "start_time": execution_start_data["start_time"] if 'execution_start_data' in locals() else datetime.now().isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "description": (
                        f"All planned nodes finished — {len(final_state.get('execution_results', {}))} result bundle(s) "
                        f"in context (replan rounds used: {replan_round})."
                    ),
                    "error": ""
                }
                try:
                    await progress_callback(execution_complete_data)
                    print(f"✅ Graph execution complete progress sent")
                except Exception as e:
                    print(f"⚠️ Error sending graph execution complete progress: {e}")
            
            # Step 3: Prepare response
            processing_time = asyncio.get_event_loop().time() - start_time
            
            # Create synthesis from a synthesize node if available; fall back gracefully otherwise
            synthesis_data = {"answer": "No synthesis available", "citations": [], "confidence": "low", "data_quality": "unknown"}
            try:
                # Prefer the latest synthesize node result
                node_id_to_type = {n.id: n.type for n in graph_plan.nodes}
                preferred_node_id = None
                for node_id in reversed(graph_plan.execution_order):
                    if node_id_to_type.get(node_id) == "synthesize" and node_id in final_state["execution_results"]:
                        preferred_node_id = node_id
                        break
                if preferred_node_id:
                    possible = final_state["execution_results"][preferred_node_id]
                    if isinstance(possible, dict):
                        synthesis_data = possible
                    elif isinstance(possible, list) and possible:
                        # Try pick a dict-like synthesis
                        first_dict = next((it for it in possible if isinstance(it, dict) and "answer" in it), None)
                        if first_dict:
                            synthesis_data = first_dict
                        else:
                            synthesis_data = {"answer": str(possible[0])}
                else:
                    # Fall back to last node if no synthesize node
                    last_node_id = graph_plan.execution_order[-1] if graph_plan.execution_order else None
                    if last_node_id and last_node_id in final_state["execution_results"]:
                        possible = final_state["execution_results"][last_node_id]
                        if isinstance(possible, dict):
                            synthesis_data = possible
                        elif isinstance(possible, list):
                            # Try to extract a dict with answer or fall back to a generic message
                            first_dict = next((it for it in possible if isinstance(it, dict) and "answer" in it), None)
                            if first_dict:
                                synthesis_data = first_dict
                            else:
                                synthesis_data = {
                                    "answer": "Protocol generation completed successfully",
                                    "citations": [],
                                    "confidence": "high",
                                    "data_quality": "good"
                                }
            except Exception:
                pass
            
            synthesis = Synthesis(
                answer=synthesis_data.get("answer", "Analysis completed"),
                citations=synthesis_data.get("citations", []),
                confidence=synthesis_data.get("confidence", "medium"),
                data_quality=synthesis_data.get("data_quality", "unknown")
            )
            
            metadata = Metadata(
                query_timestamp=start_time,
                sources_used=list(set([node.parameters.get("source") for node in graph_plan.nodes if node.parameters.get("source")])),
                processing_time=processing_time,
                total_results=len(final_state["execution_results"]),
                deep_research_run_id=run_id if dr_enabled else None,
                deep_research_replan_rounds=replan_round,
                deep_research_verifier_passed=verifier_passed,
                deep_research_parallel_subruns=parallel_subruns_merged,
            )
            
            response = DynamicQueryResponse(
                query=query,
                graph_plan=graph_plan if include_graph_plan else None,
                results=final_state["execution_results"],
                synthesis=synthesis,
                metadata=metadata,
                execution_trace=final_state["execution_trace"],
                context_manager=final_state.get("context_manager")
            )
            
            # Cache the response
            cache_manager.set(cache_key, response)
            
            # Log performance
            log_performance("Dynamic query processing", processing_time)
            
            print(f"✅ Dynamic query completed in {processing_time:.2f}s")
            return response
            
        except Exception as e:
            log_error(e, "Dynamic query processing")
            processing_time = asyncio.get_event_loop().time() - start_time
            
            # Return error response
            return DynamicQueryResponse(
                query=query,
                graph_plan=None,
                results={},
                synthesis=Synthesis(
                    answer=f"Error processing query: {str(e)}",
                    citations=[],
                    confidence="low",
                    data_quality="unknown"
                ),
                metadata=Metadata(
                    query_timestamp=start_time,
                    sources_used=[],
                    processing_time=processing_time,
                    total_results=0
                ),
                execution_trace=[]
            )

    async def process_dynamic_query_with_plan(self, query: str, custom_plan: GraphPlan) -> DynamicQueryResponse:
        """Process a query using a custom graph plan (for testing)"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            custom_plan = self._sanitize_dynamic_chat_plan(custom_plan, deep_plan=True)
            # Log the query
            log_query(f"Dynamic query with custom plan: {query}")
            
            # Create the dynamic graph from the custom plan
            graph = self._create_dynamic_graph(custom_plan)
            
            # Initialize state (context_manager required by graph nodes / synthesis paths)
            initial_state = DynamicGraphState(
                query=query,
                graph_plan=custom_plan.dict(),
                execution_results={},
                current_step="",
                execution_trace=[],
                error="",
                context_manager=ContextManager(query=query),
            )
            
            # Execute the graph
            print(f"🚀 Executing custom graph with {len(custom_plan.nodes)} nodes")
            result = await graph.ainvoke(
                initial_state,
                config=_langgraph_invoke_config(len(custom_plan.execution_order)),
            )
            
            # Extract results
            execution_time = asyncio.get_event_loop().time() - start_time
            
            # Get the final synthesis result
            final_result = None
            for node_id in reversed(custom_plan.execution_order):
                if node_id in result["execution_results"]:
                    node_result = result["execution_results"][node_id]
                    if isinstance(node_result, dict) and "summary" in node_result:
                        final_result = node_result
                        break
            
            if not final_result:
                # Fallback to last result
                for node_id in reversed(custom_plan.execution_order):
                    if node_id in result["execution_results"]:
                        node_result = result["execution_results"][node_id]
                        if isinstance(node_result, list):
                            for item in node_result:
                                if isinstance(item, dict) and "answer" in item:
                                    final_result = item
                                    break
                            if final_result is None:
                                final_result = {
                                    "answer": "Analysis completed",
                                    "citations": [],
                                    "confidence": "medium",
                                    "data_quality": "unknown",
                                }
                        else:
                            final_result = node_result
                        break
            
            # Create response
            response = DynamicQueryResponse(
                query=query,
                graph_plan=custom_plan,
                results=result.get("execution_results", {}),
                synthesis=Synthesis(
                    answer=final_result.get("answer", "Analysis completed") if isinstance(final_result, dict) else str(final_result),
                    citations=final_result.get("citations", []) if isinstance(final_result, dict) else [],
                    confidence=final_result.get("confidence", "medium") if isinstance(final_result, dict) else "medium",
                    data_quality=final_result.get("data_quality", "unknown") if isinstance(final_result, dict) else "unknown"
                ),
                metadata=Metadata(
                    query_timestamp=start_time,
                    sources_used=list(set([node.parameters.get("source") for node in custom_plan.nodes if node.parameters.get("source")])),
                    processing_time=execution_time,
                    total_results=len(result.get("execution_results", {}))
                ),
                execution_trace=result.get("execution_trace", [])
            )
            
            # Cache the result
            cache_key = f"dynamic_query_custom:{hash(query)}"
            cache_manager.set(cache_key, response)
            print(response)
            return response
            
        except Exception as e:
            log_error(e, "Dynamic query with custom plan")
            return DynamicQueryResponse(
                query=query,
                graph_plan=custom_plan,
                results={},
                synthesis=Synthesis(
                    answer=f"Error processing query: {str(e)}",
                    citations=[],
                    confidence="low",
                    data_quality="error"
                ),
                metadata=Metadata(
                    query_timestamp=start_time,
                    sources_used=[],
                    processing_time=asyncio.get_event_loop().time() - start_time,
                    total_results=0
                ),
                execution_trace=[]
            )

    async def process_simple_query(self, query: str, conversation_history: List[Dict] = None) -> SimpleQueryResponse:
        """Process a query and return only the synthesis answer without raw data"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Log the query
            log_query(f"Simple query: {query}")
            
            # Check cache first
            conversation_hash = hash(str(conversation_history)) if conversation_history else 0
            cache_key = f"simple_query:{hash(query)}_{conversation_hash}"
            cached_response = cache_manager.get(cache_key)
            
            if cached_response:
                return cached_response
            
            # Step 1: Assess query and create graph plan
            print(f"🔍 Assessing query and planning graph for: {query}")
            graph_plan = await self.assess_query_and_plan_graph(query, conversation_history, deep_plan=False)
            print(f"✅ Graph plan created with {len(graph_plan.nodes)} nodes")

            # Log detailed graph plan structure (added for simple query)
            print("\n📊 GRAPH PLAN DETAILS:")
            print("=" * 60)
            print(f"REASONING: {graph_plan.reasoning}")
            print(f"EXECUTION ORDER: {' → '.join(graph_plan.execution_order)}")
            print(f"TOTAL EDGES: {len(graph_plan.edges)}")
            print("\nNODES:")
            print("-" * 40)
            for i, node in enumerate(graph_plan.nodes, 1):
                print(f"{i}. {node.id} ({node.type})")
                print(f"   Description: {node.description}")
                print(f"   Parameters: {node.parameters}")
                print(f"   Dependencies: {node.dependencies}")
                print()
            print("EDGES:")
            print("-" * 40)
            for i, edge in enumerate(graph_plan.edges, 1):
                print(f"{i}. {edge['from']} → {edge['to']}")
            print("=" * 60)
            
            # Step 2: Create and execute the dynamic graph
            dynamic_graph = self._create_dynamic_graph(graph_plan)
            
            # Initialize state with enhanced context management
            context_manager = ContextManager(query=query)
            
            # Add conversation history to context manager if available (optional middle summarization)
            if conversation_history:
                conv_dicts = conversation_messages_to_dicts(conversation_history)
                conv_dicts = await maybe_summarize_conversation_messages(conv_dicts)
                for message in conv_dicts:
                    role = message.get("role", "unknown")
                    content = message.get("content", "")
                    timestamp = message.get("timestamp", 0)
                    meta = {k: v for k, v in message.items() if k not in ("role", "content", "timestamp")}
                    context_manager.add_context_item(
                        layer_type="conversation",
                        content={"role": role, "content": content},
                        source="conversation_history",
                        node_id="conversation",
                        metadata={"timestamp": timestamp, **meta},
                    )
            
            initial_state = DynamicGraphState(
                query=query,
                graph_plan=graph_plan.dict(),
                execution_results={},
                current_step="",
                execution_trace=[],
                error="",
                context_manager=context_manager
            )
            
            # Execute the graph
            final_state = await dynamic_graph.ainvoke(
                initial_state,
                config=_langgraph_invoke_config(len(graph_plan.execution_order)),
            )
            
            # Step 3: Prepare simplified response
            processing_time = asyncio.get_event_loop().time() - start_time
            
            # Create synthesis from final results
            synthesis_data = final_state["execution_results"].get(
                graph_plan.execution_order[-1], 
                {"answer": "No synthesis available", "citations": [], "confidence": "low", "data_quality": "unknown"}
            )
            
            if isinstance(synthesis_data, list):
                synthesis_dict = None
                for item in synthesis_data:
                    if isinstance(item, dict) and "answer" in item:
                        synthesis_dict = item
                        break
                
                if synthesis_dict is None:
                    synthesis_dict = {
                        "answer": "Analysis completed",
                        "citations": [],
                        "confidence": "medium",
                        "data_quality": "unknown",
                    }
                
                synthesis_data = synthesis_dict
            
            # Extract sources used
            sources_used = list(set([
                node.parameters.get("source") 
                for node in graph_plan.nodes 
                if node.parameters.get("source")
            ]))
            
            # Create simplified response
            response = SimpleQueryResponse(
                query=query,
                answer=synthesis_data.get("answer", "Analysis completed"),
                citations=synthesis_data.get("citations", []),
                confidence=synthesis_data.get("confidence", "medium"),
                data_quality=synthesis_data.get("data_quality", "unknown"),
                processing_time=processing_time,
                sources_used=sources_used
            )
            
            # Cache the response
            cache_manager.set(cache_key, response)
            
            # Log performance
            log_performance("Simple query processing", processing_time)
            
            print(f"✅ Simple query completed in {processing_time:.2f}s")
            return response
            
        except Exception as e:
            log_error(e, "Simple query processing")
            processing_time = asyncio.get_event_loop().time() - start_time
            
            # Return error response
            return SimpleQueryResponse(
                query=query,
                answer=f"Error processing query: {str(e)}",
                citations=[],
                confidence="low",
                data_quality="unknown",
                processing_time=processing_time,
                sources_used=[]
            )

    def _create_rich_citation(self, content: dict, layer_type: str) -> str:
        """Human-readable citation line (e.g. protocol reference lists); URLs appended when known."""
        try:
            link = citation_link_from_content(content, layer_type)
            if link:
                if link.get("url"):
                    return f"{link['text']} | URL: {link['url']}"
                return link["text"]
            if "nct_id" in content:
                return f"NCT{content['nct_id']}"
            if "pmid" in content:
                return f"PMID{content['pmid']}"
            if "url" in content and content.get("url"):
                return str(content["url"])
            return str(content.get("title", content.get("name", "Unknown source")))
        except Exception:
            if isinstance(content, dict) and "nct_id" in content:
                return f"NCT{content['nct_id']}"
            if isinstance(content, dict) and "pmid" in content:
                return f"PMID{content['pmid']}"
            return "Unknown source"

    async def _build_dynamic_search_query(self, node: GraphNode, state: Dict, plan: GraphPlan, search_focus: str) -> str:
        """Build a dynamic search query based on previous node results and dependencies"""
        try:
            # If no dependencies, use the original search focus or query
            if not node.dependencies:
                if search_focus:
                    return search_focus
                else:
                    return state["query"]
            
            # Get results from dependent nodes
            dependent_data = {}
            for dep_node_id in node.dependencies:
                if dep_node_id in state["execution_results"]:
                    dep_data = state["execution_results"][dep_node_id]
                    dependent_data[dep_node_id] = dep_data
            
            # If no dependent data available, fallback to search_focus or original query
            if not dependent_data:
                if search_focus:
                    return search_focus
                else:
                    return state["query"]
            
            # Build dynamic query using LLM
            dynamic_query_prompt = f"""You are an expert search query builder. Create a search query for the following search node based on results from its dependent nodes.

ORIGINAL QUERY: {state['query']}

SEARCH NODE: {node.id}
SEARCH NODE DESCRIPTION: {node.description}
SEARCH FOCUS: {search_focus}

DEPENDENT NODE RESULTS:"""
            
            # Add dependent node results to the prompt
            for dep_node_id, dep_data in dependent_data.items():
                dep_node = next((n for n in plan.nodes if n.id == dep_node_id), None)
                dep_description = dep_node.description if dep_node else dep_node_id
                
                dynamic_query_prompt += f"\n{dep_node_id} ({dep_description}):\n"
                
                # Format the dependent data for the prompt
                if isinstance(dep_data, list) and dep_data:
                    # For extraction nodes, look for extracted content
                    if dep_data and isinstance(dep_data[0], dict) and "extracted" in dep_data[0]:
                        extracted_content = dep_data[0]["extracted"]
                        dynamic_query_prompt += f"Extracted: {extracted_content[:1200]}...\n"      
                    # For analysis nodes, look for analysis content
                    elif dep_data and isinstance(dep_data[0], dict) and "analysis" in dep_data[0]:
                        analysis_content = dep_data[0]["analysis"]
                        dynamic_query_prompt += f"Analysis: {analysis_content[:1200]}...\n"
                    # For search nodes, show sample titles/names
                    else:
                        sample_items = dep_data[:6]  # Increased from 3 to 6 for better pattern recognition
                        for item in sample_items:
                            if isinstance(item, dict):
                                title = item.get('title', item.get('name', 'No title'))
                                dynamic_query_prompt += f"- {title[:250]}...\n"
                elif isinstance(dep_data, dict):
                    # Handle dict results
                    dynamic_query_prompt += f"Result: {json.dumps(dep_data, indent=2)[:1200]}...\n"
                else:
                    dynamic_query_prompt += f"Result: {str(dep_data)[:1200]}...\n"
            
            dynamic_query_prompt += """

INSTRUCTIONS:
1. Create a search query that uses the information from the dependent nodes
2. Focus on the search nodes description and search_focus
3. Extract key terms, names, or identifiers from the dependent results
4. Build a query that will find relevant information for the current search
5. If the dependent nodes extracted specific names, use those names in the query
6. If the dependent nodes found specific identifiers (like NPI numbers), use those in the query
7. Make the query specific and actionable
8. Search-string language: use the **language of the jurisdiction or primary sources** for this node (e.g. Chinese keywords for Chinese regulations/NMPA even when ORIGINAL QUERY is English). If the topic is US FDA or global English sources, English is appropriate. Do not force English when the search target is regional primary-language content.
9. Return ONLY the search term with no additonal text or formatting

EXAMPLES:
- If dependent node extracted "Dr. John Smith" and current node searches for clinical trials, use: "Dr. John Smith clinical trials investigator"
- If dependent node found NPI "1234567890" and current node searches for accreditation, use: "NPI 1234567890 clinical trial accreditation"
- If dependent node analyzed sponsor data and current node searches for market info, use: "Merck ulcerative colitis market analysis"
- If ORIGINAL QUERY is English but the node targets Chinese regulatory rules, use Chinese search terms, e.g. "国家药监局 药物临床试验质量管理规范"

SEARCH QUERY:"""
            
            # Get dynamic query from LLM
            dynamic_query_response = await llm_agent.generate_response(dynamic_query_prompt)
            
            # Clean up the response
            dynamic_query = dynamic_query_response.strip()
            
            # Remove quotes if present
            if dynamic_query.startswith('"') and dynamic_query.endswith('"'):
                dynamic_query = dynamic_query[1:-1]
            elif dynamic_query.startswith("'") and dynamic_query.endswith("'"):
                dynamic_query = dynamic_query[1:-1]
            
            # If LLM failed to generate a good query, fallback to search_focus
            if not dynamic_query or len(dynamic_query) < 5:
                if search_focus:
                    return search_focus
                else:
                    return state["query"]
            
            return dynamic_query
            
        except Exception as e:
            print(f"❌ Error building dynamic search query: {e}")
            # Fallback to search_focus or original query
            if search_focus:
                return search_focus
            else:
                return state["query"]

    def _truncate_soa_data_for_synthesis(self, soa_table_data, dynamic_limit: int = None):
        """Intelligently truncate SoA table data dynamically based on actual data size"""
        if not soa_table_data:
            return []
        
        # Use dynamic limit if provided, otherwise use conservative default
        max_tables = dynamic_limit if dynamic_limit else 15
        max_table_data_rows = 12  # Keep this fixed for readability
        
        if len(soa_table_data) <= max_tables:
            # If we're under the limit, just truncate table data rows
            truncated_data = []
            for table in soa_table_data:
                if isinstance(table, dict):
                    truncated_table = table.copy()
                    # Truncate table_data if it's too long
                    if 'table_data' in truncated_table and isinstance(truncated_table['table_data'], list):
                        truncated_table['table_data'] = truncated_table['table_data'][:max_table_data_rows]
                        if len(table['table_data']) > max_table_data_rows:
                            truncated_table['table_data_truncated'] = True
                            truncated_table['original_row_count'] = len(table['table_data'])
                    truncated_data.append(truncated_table)
                else:
                    truncated_data.append(table)
            return truncated_data
        else:
            # If we have too many tables, prioritize by confidence and relevance
            # Sort by confidence score (higher is better) and take top tables
            sorted_tables = sorted(
                soa_table_data,
                key=lambda x: (
                    x.get('confidence_score', 0) if isinstance(x, dict) else 0,
                    x.get('page_number', 0) if isinstance(x, dict) else 0
                ),
                reverse=True
            )
            
            # Take top tables and truncate their data
            top_tables = sorted_tables[:max_tables]
            truncated_data = []
            
            for table in top_tables:
                if isinstance(table, dict):
                    truncated_table = table.copy()
                    # Truncate table_data if it's too long
                    if 'table_data' in truncated_table and isinstance(truncated_table['table_data'], list):
                        truncated_table['table_data'] = truncated_table['table_data'][:max_table_data_rows]
                        if len(table['table_data']) > max_table_data_rows:
                            truncated_table['table_data_truncated'] = True
                            truncated_table['original_row_count'] = len(table['table_data'])
                    truncated_data.append(truncated_table)
                else:
                    truncated_data.append(table)
            
            # Add metadata about truncation
            if len(soa_table_data) > max_tables:
                truncated_data.append({
                    'truncation_info': f"Data truncated from {len(soa_table_data)} to {len(truncated_data)} tables to prevent token limit exceeded",
                    'original_count': len(soa_table_data),
                    'truncated_count': len(truncated_data),
                    'max_tables_limit': max_tables,
                    'max_rows_per_table': max_table_data_rows
                })
            
            return truncated_data

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (more conservative approximation: 1 token ≈ 3 characters)"""
        return _tu_estimate_tokens(text)

    def _estimate_data_tokens(self, data: any) -> int:
        """Estimate token count for structured data"""
        return _tu_estimate_data_tokens(data)

    def _calculate_dynamic_limits(self, data_sources: dict, target_max_tokens: Optional[int] = None) -> dict:
        """Calculate dynamic limits based on actual data sizes and sources"""
        tgt = (
            target_max_tokens
            if target_max_tokens is not None
            else settings.meaningful_data_truncation_token_budget()
        )
        return _tu_calculate_dynamic_limits(data_sources, tgt)

    def _truncate_section_to_tokens(self, section: str, max_tokens: int) -> str:
        """Shrink a single section to approximately max_tokens (best-effort)."""
        return _tu_truncate_section_to_tokens(section, max_tokens)

    def _progressive_truncation(self, prompt: str, target_tokens: int = 150000) -> str:
        """Scale every `===...===` section proportionally so no tail sections are dropped."""
        return _tu_progressive_truncation(prompt, target_tokens)

    def _emergency_truncation(self, prompt: str, target_tokens: int = 120000) -> str:
        """Emergency truncation for extreme cases - very aggressive"""
        return _tu_emergency_truncation(prompt, target_tokens)

    async def _synthesis_with_fallback(
        self,
        user_content: str,
        system_prompt: Optional[str] = None,
        *,
        use_prompt_cache: bool = False,
        max_retries: int = 3,
    ) -> str:
        """Synthesis with fallback; truncates user_content only (system stays intact)."""
        from agents.llm_agent import LLMAgent
        llm_agent = LLMAgent()
        sp = system_prompt or ""
        user_h = user_content
        _sp_tok = self._estimate_tokens(sp)
        _soft = settings.synthesis_combined_prompt_soft_limit()
        _input_budget = settings.effective_synthesis_input_token_budget()

        def _combined_tokens(u: str) -> int:
            return self._estimate_tokens(sp + "\n" + u)

        for attempt in range(max_retries):
            try:
                print(f"🔄 Synthesis attempt {attempt + 1}/{max_retries}")
                return await llm_agent.generate_synthesis_response(
                    user_content=user_h,
                    system_prompt=sp or None,
                    use_prompt_cache=use_prompt_cache and attempt == 0,
                )

            except Exception as e:
                error_msg = str(e)
                print(f"❌ Synthesis attempt {attempt + 1} failed: {error_msg}")

                if "rate_limit_error" in error_msg or "429" in error_msg:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 30
                        print(f"⏳ Rate limit hit, waiting {wait_time}s before retry...")
                        await asyncio.sleep(wait_time)
                        # Input TPM limits are tight; shrink aggressively before retry.
                        if attempt == 0:
                            target_tokens = min(48_000, max(24_000, _input_budget // 3))
                        else:
                            target_tokens = max(24_000, int(_input_budget * 0.55) - (attempt * 22_000))
                        user_h = self._progressive_truncation(user_h, target_tokens)
                        if attempt >= 1 and "WORKING ANSWER" in user_h and "ENHANCED CONTEXT" in user_h:
                            try:
                                wa_i = user_h.index("WORKING ANSWER")
                                ec_i = user_h.index("ENHANCED CONTEXT", wa_i)
                                wa_block = user_h[wa_i:ec_i]
                                tail = user_h[ec_i:]
                                tail_trim = self._progressive_truncation(tail, max(12000, target_tokens // 2))
                                user_h = wa_block + "\n\n" + tail_trim
                            except ValueError:
                                pass
                        print(f"📉 Retry with user-content token budget ~{target_tokens:,}")
                        continue
                    return self._generate_fallback_response(user_h)

                if "token" in error_msg.lower() or "400" in error_msg:
                    if attempt < max_retries - 1:
                        target_tokens = max(
                            16_000,
                            int(settings.synthesis_user_progressive_target_tokens(_sp_tok) * 0.85)
                            - (attempt * 24_000),
                        )
                        user_h = self._progressive_truncation(user_h, target_tokens)
                        print(f"📉 Token limit hit, retrying with truncated user content (~{target_tokens:,})")
                        if _combined_tokens(user_h) > _soft:
                            user_h = self._emergency_truncation(
                                user_h,
                                settings.synthesis_user_emergency_target_tokens(_sp_tok),
                            )
                        continue
                    return self._generate_fallback_response(user_h)

                return self._generate_fallback_response(user_h)

        return self._generate_fallback_response(user_h)

    def _generate_fallback_response(self, prompt: str) -> str:
        """Generate a fallback response when synthesis fails"""
        # Extract key information from the prompt for a basic response
        query_match = prompt.split("ORIGINAL QUERY:")[1].split("\n")[0].strip() if "ORIGINAL QUERY:" in prompt else "clinical research query"

        wa_snip = ""
        if "WORKING ANSWER" in prompt and "ENHANCED CONTEXT" in prompt:
            try:
                wa_i = prompt.index("WORKING ANSWER")
                ec_i = prompt.index("ENHANCED CONTEXT", wa_i)
                wa_snip = prompt[wa_i:ec_i].strip()
                if len(wa_snip) > 14000:
                    wa_snip = wa_snip[:14000] + "\n\n…[truncated]"
            except ValueError:
                wa_snip = ""

        draft_block = (
            f"\n\n### Incremental research draft (best-effort)\n\n{wa_snip}\n\n"
            if wa_snip
            else ""
        )

        fallback_response = f"""
I apologize, but I encountered technical limitations while processing your query: "{query_match}".

The system gathered comprehensive data from multiple sources, but was unable to complete the full synthesis due to rate limits or token constraints.{draft_block}
**Data Sources Available:**
- Clinical trial data from multiple databases
- Research publications and literature
- Regulatory information and endpoints
- Schedule of Activities (SoA) data

**Recommendation:**
Please try rephrasing your query to be more specific, or break it into smaller, more focused questions. The system has successfully gathered the relevant data and can provide detailed analysis with more targeted queries.

**Alternative Approaches:**
1. Ask about specific trial phases or conditions
2. Focus on particular endpoints or outcomes
3. Request analysis of specific data sources
4. Break complex queries into multiple simpler ones

The underlying data is available and the system is functioning correctly - the limitation is in the synthesis step due to the large volume of information gathered.
"""
        return fallback_response

    def _truncate_trial_summaries_for_synthesis(self, trial_summaries, dynamic_limit: int = None):
        """Truncate trial summaries dynamically based on actual data size"""
        if not trial_summaries:
            return []
        
        # Use dynamic limit if provided, otherwise use conservative default
        max_summaries = dynamic_limit if dynamic_limit else 20
        max_summary_length = 12_000
        
        if len(trial_summaries) <= max_summaries:
            # If we're under the limit, just truncate summary text
            truncated_summaries = []
            for summary in trial_summaries:
                if isinstance(summary, dict):
                    truncated_summary = summary.copy()
                    # Truncate summary text if it's too long
                    if 'summary' in truncated_summary and isinstance(truncated_summary['summary'], str):
                        truncated_summary['summary'] = truncated_summary['summary'][:max_summary_length]
                        if len(summary['summary']) > max_summary_length:
                            truncated_summary['summary_truncated'] = True
                            truncated_summary['original_length'] = len(summary['summary'])
                    truncated_summaries.append(truncated_summary)
                else:
                    truncated_summaries.append(summary)
            return truncated_summaries
        else:
            # If we have too many summaries, prioritize by relevance and take top summaries
            # Sort by relevance score (higher is better) and take top summaries
            sorted_summaries = sorted(
                trial_summaries,
                key=lambda x: (
                    x.get('relevance_score', 0) if isinstance(x, dict) else 0,
                    x.get('page_number', 0) if isinstance(x, dict) else 0
                ),
                reverse=True
            )
            
            # Take top summaries and truncate their text
            top_summaries = sorted_summaries[:max_summaries]
            truncated_summaries = []
            
            for summary in top_summaries:
                if isinstance(summary, dict):
                    truncated_summary = summary.copy()
                    # Truncate summary text if it's too long
                    if 'summary' in truncated_summary and isinstance(truncated_summary['summary'], str):
                        truncated_summary['summary'] = truncated_summary['summary'][:max_summary_length]
                        if len(summary['summary']) > max_summary_length:
                            truncated_summary['summary_truncated'] = True
                            truncated_summary['original_length'] = len(summary['summary'])
                    truncated_summaries.append(truncated_summary)
                else:
                    truncated_summaries.append(summary)
            
            # Add metadata about truncation
            if len(trial_summaries) > max_summaries:
                truncated_summaries.append({
                    'truncation_info': f"Data truncated from {len(trial_summaries)} to {len(truncated_summaries)} summaries to prevent token limit exceeded",
                    'original_count': len(trial_summaries),
                    'truncated_count': len(truncated_summaries),
                    'max_summaries_limit': max_summaries,
                    'max_length_per_summary': max_summary_length
                })
            
            return truncated_summaries


# No eager global engine: importing this module already loads heavy agent singletons.
# The app sets `reasoning_engine` in main_complete after data is ready (see lifespan).