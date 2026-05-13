"""
LangGraph Reasoning Engine for Clinical Research Assistant
"""
import asyncio
import json
from typing import Dict, List, Any, Optional, TypedDict
from datetime import datetime
from langgraph.graph import StateGraph, END
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
from processing.data_processor import data_processor
from models.schemas import QueryResponse, SynthesisResult, QueryMetadata, QueryRequest, QueryResults, Synthesis, Metadata
import uuid
import logging

# Define the state schema
class GraphState(TypedDict):
    query: str
    query_results: Dict[str, List[Any]]
    synthesis: Dict[str, Any]
    metadata: Dict[str, Any]
    current_step: str
    error: str

logger = logging.getLogger(__name__)

def create_reasoning_graph():
    """Create the reasoning graph"""
    
    def analyze_query(state: GraphState) -> GraphState:
        """Analyze and plan the query"""
        try:
            state["current_step"] = "analyzing"
            state["query_results"] = {
                "clinical_trials": [],
                "publications": [],
                "biomcp_data": [],
                "aact_data": [],
                "openfda_data": []
            }
            state["synthesis"] = {}
            state["metadata"] = {
                "sources_used": [],
                "processing_time": 0
            }
            state["error"] = ""
            return state
        except Exception as e:
            state["error"] = f"Query analysis failed: {str(e)}"
            return state
    
    async def gather_clinical_trials(state: GraphState) -> GraphState:
        """Gather clinical trials data"""
        try:
            state["current_step"] = "gathering_clinical_trials"
            query = state["query"]
            
            print(f"🔍 Searching clinical trials for: {query}")
            
            # Search for clinical trials
            trials = await clinical_trials_agent.search_studies(query, max_results=20)
            state["query_results"]["clinical_trials"] = [trial.dict() for trial in trials]
            state["metadata"]["sources_used"].append("clinical_trials")
            
            print(f"✅ Found {len(trials)} clinical trials")
            
            return state
        except Exception as e:
            log_error(e, "Clinical trials gathering")
            print(f"❌ Clinical trials error: {e}")
            state["query_results"]["clinical_trials"] = []
            return state
    
    async def gather_publications(state: GraphState) -> GraphState:
        """Gather publications data"""
        try:
            state["current_step"] = "gathering_publications"
            query = state["query"]
            
            print(f"🔍 Searching publications for: {query}")
            
            # Search for publications
            publications = await pubmed_agent.search_publications(query, max_results=20)
            state["query_results"]["publications"] = [pub.dict() for pub in publications]
            state["metadata"]["sources_used"].append("publications")
            
            print(f"✅ Found {len(publications)} publications")
            
            return state
        except Exception as e:
            log_error(e, "Publications gathering")
            print(f"❌ Publications error: {e}")
            state["query_results"]["publications"] = []
            return state
    
    async def gather_biomcp_data(state: GraphState) -> GraphState:
        """Gather BioMCP data"""
        try:
            state["current_step"] = "gathering_biomcp"
            query = state["query"]
            
            print(f"🔍 Searching BioOntology for: {query}")
            
            # Search for BioMCP data
            biomcp_results = await biomcp_agent.search_data(query, max_results=20)
            state["query_results"]["biomcp_data"] = [item.dict() for item in biomcp_results]
            state["metadata"]["sources_used"].append("biomcp_data")
            
            print(f"✅ Found {len(biomcp_results)} BioOntology results")
            
            return state
        except Exception as e:
            log_error(e, "BioMCP data gathering")
            print(f"❌ BioOntology error: {e}")
            state["query_results"]["biomcp_data"] = []
            return state
    
    async def gather_aact_data(state: GraphState) -> GraphState:
        """Gather AACT data"""
        try:
            state["current_step"] = "gathering_aact"
            query = state["query"]
            
            print(f"🔍 Searching AACT for: {query}")
            
            # Search for AACT data
            aact_results = await aact_agent.search_studies(query, max_results=20)
            state["query_results"]["aact_data"] = [item.dict() for item in aact_results]
            state["metadata"]["sources_used"].append("aact_data")
            
            print(f"✅ Found {len(aact_results)} AACT results")
            
            return state
        except Exception as e:
            log_error(e, "AACT data gathering")
            print(f"❌ AACT error: {e}")
            state["query_results"]["aact_data"] = []
            return state
    
    async def gather_openfda_data(state: GraphState) -> GraphState:
        """Gather OpenFDA data"""
        try:
            state["current_step"] = "gathering_openfda"
            query = state["query"]
            
            print(f"🔍 Searching OpenFDA for: {query}")
            
            # Create OpenFDA agent instance
            openfda_agent = OpenFDAAgent()
            
            # Search for OpenFDA data
            openfda_results = await openfda_agent.search_drugs(query, max_results=20)
            state["query_results"]["openfda_data"] = [item.dict() for item in openfda_results]
            state["metadata"]["sources_used"].append("openfda_data")
            
            print(f"✅ Found {len(openfda_results)} OpenFDA results")
            
            return state
        except Exception as e:
            log_error(e, "OpenFDA data gathering")
            print(f"❌ OpenFDA error: {e}")
            state["query_results"]["openfda_data"] = []
            return state
    
    async def gather_fierce_pharma_data(state: GraphState) -> GraphState:
        """Gather Fierce Pharma news data"""
        try:
            state["current_step"] = "gathering_fierce_pharma"
            query = state["query"]
            
            print(f"🔍 Searching Fierce Pharma news for: {query}")
            
            # Use the Google Search agent
            from agents.fierce_pharma_agent import google_search_agent
            
            # Search for web information
            google_search_results = await google_search_agent.search_web(query, max_results=20)
            state["query_results"]["fierce_pharma_data"] = [item.dict() for item in google_search_results]
            state["metadata"]["sources_used"].append("fierce_pharma_data")
            
            print(f"✅ Found {len(google_search_results)} web search results")
            
            return state
        except Exception as e:
            log_error(e, "Fierce Pharma data gathering")
            print(f"❌ Fierce Pharma error: {e}")
            state["query_results"]["fierce_pharma_data"] = []
            return state
    
    async def synthesize_results(state: GraphState) -> GraphState:
        """Synthesize all results using LLM"""
        try:
            state["current_step"] = "synthesizing"
            
            # Prepare data for synthesis
            clinical_trials = state["query_results"]["clinical_trials"]
            publications = state["query_results"]["publications"]
            biomcp_data = state["query_results"]["biomcp_data"]
            aact_data = state["query_results"]["aact_data"]
            openfda_data = state["query_results"]["openfda_data"]
            
    
            
            fierce_pharma_data = state["query_results"]["fierce_pharma_data"]
            # Check if we have any results
            total_results = len(clinical_trials) + len(publications) + len(biomcp_data) + len(aact_data) + len(openfda_data) + len(fierce_pharma_data)
            
            if total_results == 0:
                # No results found, create a helpful response
                synthesis = {
                    "summary": f"No specific clinical research data found for '{state['query']}'. This could be due to: 1) Limited data availability, 2) Query specificity, or 3) API service limitations. Consider refining your search terms or checking back later.",
                    "key_findings": [],
                    "recommendations": [
                        "Try using more specific medical terms",
                        "Search for broader categories",
                        "Check spelling of medical terms",
                        "Consider alternative search strategies"
                    ]
                }
            else:
                # Prepare context for LLM
                context = f"""
                Query: {state['query']}
                
                Clinical Trials Found: {len(clinical_trials)}
                Publications Found: {len(publications)}
                BioMCP Data Found: {len(biomcp_data)}
                AACT Data Found: {len(aact_data)}
                OpenFDA Data Found: {len(openfda_data)}
                Fierce Pharma News Found: {len(fierce_pharma_data)}
                
                Clinical Trials (top 3):
                {json.dumps(clinical_trials[:3], indent=2) if clinical_trials else 'None found'}
                
                Publications (top 3):
                {json.dumps(publications[:3], indent=2) if publications else 'None found'}
                
                BioMCP Data (top 3):
                {json.dumps(biomcp_data[:3], indent=2) if biomcp_data else 'None found'}
                
                AACT Data (top 3):
                {json.dumps(aact_data[:3], indent=2) if aact_data else 'None found'}
                
                OpenFDA Data (top 3):
                {json.dumps(openfda_data[:3], indent=2) if openfda_data else 'None found'}
                
                Fierce Pharma News (top 3):
                {json.dumps(fierce_pharma_data[:3], indent=2) if fierce_pharma_data else 'None found'}
                """
                
                # Generate synthesis prompt
                synthesis_prompt = f"""
                Based on the following clinical research data, provide a comprehensive synthesis:
                
                {context}
                
                Please provide a JSON response with the following structure:
                {{
                    "summary": "A comprehensive summary of the findings",
                    "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
                    "recommendations": ["Recommendation 1", "Recommendation 2", "Recommendation 3"]
                }}
                
                Focus on:
                1. Clinical significance
                2. Research gaps
                3. Practical implications
                4. Future research directions
                5. **Traceability** — in summary, key_findings, and recommendations text, cite trial/publication identifiers from the data and **use Markdown links** `[label](url)` wherever a URL appears in the context above (do not invent URLs).
                """
                
                # Get LLM response
                llm_response = await llm_agent.generate_response(synthesis_prompt)
                
                # Try to parse JSON response
                try:
                    # Extract JSON from response if it's wrapped in markdown
                    if "```json" in llm_response:
                        json_start = llm_response.find("```json") + 7
                        json_end = llm_response.find("```", json_start)
                        json_str = llm_response[json_start:json_end].strip()
                    else:
                        json_str = llm_response.strip()
                    
                    synthesis = json.loads(json_str)
                    
                    # Validate synthesis structure
                    if not isinstance(synthesis, dict):
                        raise ValueError("Synthesis is not a dictionary")
                    
                    # Ensure required fields exist
                    synthesis = {
                        "summary": synthesis.get("summary", "Analysis completed"),
                        "key_findings": synthesis.get("key_findings", []),
                        "recommendations": synthesis.get("recommendations", [])
                    }
                    
                except (json.JSONDecodeError, ValueError) as e:
                    log_error(e, f"JSON parsing failed for synthesis: {llm_response[:200]}...")
                    # Fallback synthesis
                    fierce_pharma_data = state["query_results"].get("fierce_pharma_data", [])
                    synthesis = {
                        "summary": f"Analysis completed for '{state['query']}'. Found {len(clinical_trials)} clinical trials, {len(publications)} publications, {len(biomcp_data)} BioMCP data points, {len(aact_data)} AACT data points, {len(openfda_data)} OpenFDA data points, and {len(fierce_pharma_data)} Fierce Pharma news articles. Please review the detailed results below.",
                        "key_findings": [
                            f"Found {len(clinical_trials)} relevant clinical trials",
                            f"Found {len(publications)} relevant publications", 
                            f"Found {len(biomcp_data)} relevant BioMCP data points",
                            f"Found {len(aact_data)} relevant AACT data points",
                            f"Found {len(openfda_data)} relevant OpenFDA data points",
                            f"Found {len(fierce_pharma_data)} relevant Fierce Pharma news articles"
                        ],
                        "recommendations": [
                            "Review individual results for detailed information",
                            "Consider refining search terms for more specific results",
                            "Check trial status and eligibility criteria"
                        ]
                    }
            
            state["synthesis"] = synthesis
            print(f"✅ Synthesis completed with {len(synthesis.get('key_findings', []))} findings")
            
            return state
            
        except Exception as e:
            log_error(e, "Results synthesis")
            print(f"❌ Synthesis error: {e}")
            state["synthesis"] = {
                "summary": f"Unable to synthesize results due to processing error: {str(e)}",
                "key_findings": [],
                "recommendations": ["Please try again later or contact support"]
            }
            return state
    
    def finalize_response(state: GraphState) -> GraphState:
        """Finalize the response"""
        try:
            state["current_step"] = "finalizing"
            
            # Add metadata - use time.time() instead of asyncio.get_event_loop().time()
            import time
            state["metadata"]["query_timestamp"] = time.time()
            state["metadata"]["total_results"] = (
                len(state["query_results"]["clinical_trials"]) +
                len(state["query_results"]["publications"]) +
                len(state["query_results"]["biomcp_data"]) +
                len(state["query_results"]["aact_data"]) +
                len(state["query_results"]["openfda_data"]) +
                len(state["query_results"]["fierce_pharma_data"])
            )
            
            print(f"✅ Finalized response with {state['metadata']['total_results']} total results from {len(state['metadata']['sources_used'])} sources")
            
            return state
        except Exception as e:
            state["error"] = f"Response finalization failed: {str(e)}"
            print(f"❌ Finalization error: {e}")
            return state
    
    # Create the graph
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("analyze", analyze_query)
    workflow.add_node("clinical_trials", gather_clinical_trials)
    workflow.add_node("publications", gather_publications)
    workflow.add_node("biomcp", gather_biomcp_data)
    workflow.add_node("aact", gather_aact_data)
    workflow.add_node("openfda", gather_openfda_data)
    workflow.add_node("fierce_pharma", gather_fierce_pharma_data)
    workflow.add_node("synthesize", synthesize_results)
    workflow.add_node("finalize", finalize_response)
    
    # Set entry point
    workflow.set_entry_point("analyze")
    
    # Add edges
    workflow.add_edge("analyze", "clinical_trials")
    workflow.add_edge("clinical_trials", "publications")
    workflow.add_edge("publications", "biomcp")
    workflow.add_edge("biomcp", "aact")
    workflow.add_edge("aact", "openfda")
    workflow.add_edge("openfda", "fierce_pharma")
    workflow.add_edge("fierce_pharma", "synthesize")
    workflow.add_edge("synthesize", "finalize")
    workflow.add_edge("finalize", END)
    
    # Compile the graph
    return workflow.compile(checkpointer=MemorySaver())

# Global reasoning graph instance
reasoning_graph = create_reasoning_graph()

class ReasoningEngine:
    def __init__(self):
        self.graph = reasoning_graph
    
    async def process_query(self, query: str) -> QueryResponse:
        """Process a query through the reasoning engine"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Initialize state
            initial_state = {
                "query": query,
                "query_results": {
                    "clinical_trials": [],
                    "publications": [],
                    "biomcp_data": [],
                    "aact_data": [],
                    "openfda_data": [],
                    "fierce_pharma_data": []
                },
                "synthesis": {},
                "metadata": {
                    "query_timestamp": start_time,
                    "sources_used": [],
                    "processing_time": 0,
                    "total_results": 0
                },
                "current_step": "",
                "error": ""
            }
            
            # Generate a unique thread_id for this query
            thread_id = str(uuid.uuid4())
            config = {"configurable": {"thread_id": thread_id}}
            
            print("[DEBUG] Initial state for graph:", initial_state)
            print("[DEBUG] Config for graph:", config)
            logger.info(f"[DEBUG] Initial state for graph: {initial_state}")
            logger.info(f"[DEBUG] Config for graph: {config}")
            
            # Run the graph with config
            final_state = await self.graph.ainvoke(initial_state, config=config)
            print("[DEBUG] Final state from graph:", final_state)
            logger.info(f"[DEBUG] Final state from graph: {final_state}")
            
            # Check for errors
            if final_state.get("error"):
                raise Exception(final_state["error"])
            
            # Ensure final_state has the expected structure
            if not isinstance(final_state, dict):
                print(f"[DEBUG] final_state is not a dict: {type(final_state)}")
                raise Exception(f"Unexpected final_state type: {type(final_state)}")
            
            print(f"[DEBUG] final_state keys: {list(final_state.keys())}")
            
            # Handle case where final_state might be missing expected keys
            query_results = final_state.get("query_results", {})
            synthesis = final_state.get("synthesis", {})
            metadata = final_state.get("metadata", {})
            
            print(f"[DEBUG] query_results keys: {list(query_results.keys()) if isinstance(query_results, dict) else 'not a dict'}")
            print(f"[DEBUG] synthesis keys: {list(synthesis.keys()) if isinstance(synthesis, dict) else 'not a dict'}")
            print(f"[DEBUG] metadata keys: {list(metadata.keys()) if isinstance(metadata, dict) else 'not a dict'}")
            
            # Create response with safe defaults
            response = QueryResponse(
                query_results=QueryResults(
                    clinical_trials=query_results.get("clinical_trials", []) if isinstance(query_results, dict) else [],
                    publications=query_results.get("publications", []) if isinstance(query_results, dict) else [],
                    biomcp_data=query_results.get("biomcp_data", []) if isinstance(query_results, dict) else [],
                    aact_data=query_results.get("aact_data", []) if isinstance(query_results, dict) else [],
                    openfda_data=query_results.get("openfda_data", []) if isinstance(query_results, dict) else [],
                    fierce_pharma_data=query_results.get("fierce_pharma_data", []) if isinstance(query_results, dict) else []
                ),
                synthesis=Synthesis(
                    summary=synthesis.get("summary", "") if isinstance(synthesis, dict) else "",
                    key_findings=synthesis.get("key_findings", []) if isinstance(synthesis, dict) else [],
                    recommendations=synthesis.get("recommendations", []) if isinstance(synthesis, dict) else []
                ),
                metadata=Metadata(
                    query_timestamp=metadata.get("query_timestamp", start_time) if isinstance(metadata, dict) else start_time,
                    sources_used=metadata.get("sources_used", []) if isinstance(metadata, dict) else [],
                    processing_time=metadata.get("processing_time", 0) if isinstance(metadata, dict) else 0,
                    total_results=metadata.get("total_results", 0) if isinstance(metadata, dict) else 0
                )
            )
            
            return response
            
        except Exception as e:
            log_error(e, "Query processing")
            
            # Return error response
            return QueryResponse(
                query_results=QueryResults(
                    clinical_trials=[],
                    publications=[],
                    biomcp_data=[],
                    aact_data=[],
                    openfda_data=[],
                    fierce_pharma_data=[]
                ),
                synthesis=Synthesis(
                    summary=f"Error processing query: {str(e)}",
                    key_findings=[],
                    recommendations=["Please try again or contact support"]
                ),
                metadata=Metadata(
                    query_timestamp=start_time,
                    sources_used=[],
                    processing_time=asyncio.get_event_loop().time() - start_time,
                    total_results=0
                )
            )

# Global reasoning engine instance
reasoning_engine = ReasoningEngine() 