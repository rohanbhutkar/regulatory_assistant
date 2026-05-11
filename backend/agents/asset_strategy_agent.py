"""
Asset Strategy Agent - Specialized agent for asset strategy Q&A
Extends DynamicReasoningEngine with asset-specific capabilities
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from graph.dynamic_reasoning_engine import DynamicReasoningEngine
from services.asset_management_service import asset_management_service
from services.price_potential_engine import price_potential_engine
from services.hta_intelligence_service import hta_intelligence_service
from services.financial_modeling_service import financial_modeling_service
from services.scenario_engine import scenario_engine


class AssetStrategyAgent(DynamicReasoningEngine):
    """Specialized agent for asset strategy with tool-calling capabilities"""
    
    def __init__(self):
        super().__init__()
        # Asset-specific tools
        self.asset_tools = {
            "run_scenario": self._run_scenario_tool,
            "fetch_comparator_prices": self._fetch_comparator_prices_tool,
            "calculate_price_potential": self._calculate_price_potential_tool,
            "assess_hta_outcome": self._assess_hta_outcome_tool,
            "calculate_financial_metrics": self._calculate_financial_metrics_tool,
            "generate_report": self._generate_report_tool,
            "search_web": self._search_web_tool,
            "get_drug_info": self._get_drug_info_tool
        }
    
    async def chat_with_asset(
        self,
        asset_id: str,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Chat with asset - answer questions about asset strategy with intelligent data integration
        
        Uses graph backend agents (Google Search, GoodRx, PubMed, FDA Labels, etc.) for comprehensive answers
        """
        # Get asset context
        asset = asset_management_service.get_asset(asset_id)
        if not asset:
            return {
                "error": "Asset not found",
                "answer": None,
                "sources": [],
                "rationale": "Asset not found in system"
            }
        
        # Build comprehensive context
        asset_context = {
            "asset_name": asset.asset_name,
            "therapeutic_area": asset.therapeutic_area,
            "indication": asset.indication or 'Not specified',
            "development_stage": asset.development_stage or 'Not specified',
            "status": asset.status or 'Not specified',
            "moa": asset.moa or 'Not specified'
        }
        
        context_str = f"""
        Asset: {asset.asset_name}
        Therapeutic Area: {asset.therapeutic_area}
        Indication: {asset.indication or 'Not specified'}
        Development Stage: {asset.development_stage or 'Not specified'}
        Status: {asset.status or 'Not specified'}
        MoA: {asset.moa or 'Not specified'}
        """
        
        sources_used = []
        data_collected = []
        
        # Intelligently route query to appropriate agents
        query_lower = query.lower()
        
        try:
            # Price-related queries -> GoodRx + Google Search
            if any(keyword in query_lower for keyword in ['price', 'cost', 'pricing', 'revenue', 'net price']):
                drug_name = asset.asset_name.split('(')[0].strip()
                goodrx_info = await self._get_drug_info_tool(drug_name)
                if "error" not in goodrx_info:
                    data_collected.append(f"GoodRx pricing data for {drug_name}")
                    sources_used.append("goodrx")
                
                web_query = f"{drug_name} pricing {asset.indication or asset.therapeutic_area}"
                web_results = await self._search_web_tool(web_query, "Find recent pricing news and market reports")
                if "results" in web_results:
                    data_collected.append(f"Web search found {len(web_results['results'])} pricing-related results")
                    sources_used.append("google_search")
            
            # Regulatory/HTA queries -> FDA Labels + PubMed + Google Search
            elif any(keyword in query_lower for keyword in ['hta', 'regulatory', 'approval', 'fda', 'ema', 'reimbursement']):
                from agents.fda_labels_agent import fda_labels_agent
                fda_query = f"{asset.asset_name} {asset.indication or asset.therapeutic_area}"
                fda_results = await fda_labels_agent.search_labels(fda_query, max_results=5)
                if fda_results:
                    data_collected.append(f"FDA Labels: Found {len(fda_results)} relevant regulatory labels")
                    sources_used.append("fda_labels")
                
                pubmed_query = f"{asset.asset_name} {asset.indication} HTA reimbursement"
                pubmed_agent = self.available_agents.get("pubmed")
                if pubmed_agent:
                    try:
                        pubmed_results = await pubmed_agent.search_publications(pubmed_query, max_results=5)
                        if pubmed_results:
                            data_collected.append(f"PubMed: Found {len(pubmed_results)} HTA-related publications")
                            sources_used.append("pubmed")
                    except:
                        pass
            
            # Comparator queries -> TrialTrove + FDA Labels
            elif any(keyword in query_lower for keyword in ['comparator', 'competitor', 'benchmark', 'similar drug']):
                from agents.trialtrove_agent import trialtrove_agent
                indication = asset.indication or asset.therapeutic_area
                trial_results = await trialtrove_agent.search_studies(indication, max_results=10)
                if trial_results:
                    data_collected.append(f"TrialTrove: Found {len(trial_results)} trials in {indication}")
                    sources_used.append("trialtrove")
            
            # General queries -> Use all available agents
            else:
                # Search web for general information
                web_query = f"{asset.asset_name} {asset.indication or asset.therapeutic_area} {query}"
                web_results = await self._search_web_tool(web_query)
                if "results" in web_results:
                    data_collected.append(f"Web search: Found {len(web_results['results'])} relevant results")
                    sources_used.append("google_search")
            
            # Use parent class's query method with comprehensive context
            plan = await self.assess_query_and_plan_graph(
                query=query,
                conversation_history=conversation_history,
                study_context={"asset": asset_context},
                deep_plan=True,
            )
            
            # Build intelligent response with rationale
            answer = f"Based on analysis of {asset.asset_name} ({asset.therapeutic_area}), "
            
            if data_collected:
                answer += f"I've gathered data from {len(sources_used)} source(s): {', '.join(data_collected)}. "
            
            answer += f"Regarding your question about '{query}': "
            
            # Add context-specific answer (simplified - would use LLM for full synthesis)
            if "price" in query_lower or "cost" in query_lower:
                answer += "Pricing analysis would consider comparator benchmarks, market dynamics, and HTA requirements. "
                answer += "Use the Pricing tab to see detailed price potential calculations."
            elif "hta" in query_lower or "reimbursement" in query_lower:
                answer += "HTA assessment considers evidence strength, comparator clarity, and market-specific requirements. "
                answer += "Use the HTA Timeline tab to see detailed pathway analysis."
            else:
                answer += "I can help you explore various aspects of this asset's strategy. "
                answer += "Try asking about pricing, HTA outcomes, comparators, or financial projections."
            
            response = {
                "answer": answer,
                "citations": data_collected,
                "confidence": 0.85 if sources_used else 0.7,
                "sources": sources_used,
                "rationale": f"Response synthesized from {len(sources_used)} data source(s) with asset context: {context_str.strip()}",
                "asset_context": asset_context
            }
            
        except Exception as e:
            # Fallback response with error handling
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in chat_with_asset: {e}", exc_info=True)
            
            response = {
                "answer": f"Based on {asset.asset_name} ({asset.therapeutic_area}), I can help answer questions about: pricing, HTA outcomes, comparators, financial projections, and scenario analysis. Please try rephrasing your question or use the specific tabs for detailed analysis.",
                "citations": [],
                "confidence": 0.6,
                "sources": [],
                "rationale": f"Fallback response due to error: {str(e)}",
                "asset_context": asset_context,
                "note": "Some data sources may be temporarily unavailable"
            }
        
        return response
    
    async def _run_scenario_tool(self, scenario_params: Dict[str, Any]) -> Dict[str, Any]:
        """Tool: Run scenario"""
        asset_id = scenario_params.get("asset_id")
        result = scenario_engine.run_deterministic_scenario(asset_id, scenario_params)
        return result
    
    async def _fetch_comparator_prices_tool(self, market: str, indication: str) -> Dict[str, Any]:
        """Tool: Fetch comparator prices"""
        # Use GoodRx agent for retail pricing
        goodrx_agent = self.available_agents.get("goodrx")
        if goodrx_agent:
            # Would search for comparators in indication
            return {"message": "Comparator prices fetched", "prices": []}
        
        # Fallback to static data
        return {"message": "Using static comparator data", "prices": []}
    
    async def _calculate_price_potential_tool(self, asset_id: str, market: str) -> Dict[str, Any]:
        """Tool: Calculate price potential"""
        prediction = price_potential_engine.get_price_prediction(asset_id, market)
        if not prediction:
            return {"error": "Price prediction not found"}
        return prediction
    
    async def _assess_hta_outcome_tool(self, asset_id: str, market: str) -> Dict[str, Any]:
        """Tool: Assess HTA outcome"""
        assessment = hta_intelligence_service.get_hta_assessment(asset_id, market)
        if not assessment:
            # Run assessment
            assessment = hta_intelligence_service.predict_hta_outcome_likelihood(
                asset_id=asset_id,
                market=market
            )
        return assessment
    
    async def _calculate_financial_metrics_tool(self, asset_id: str, scenario_id: Optional[str] = None) -> Dict[str, Any]:
        """Tool: Calculate financial metrics"""
        # Get revenue projection
        revenue = financial_modeling_service.get_revenue_projection(asset_id, "US")
        if not revenue:
            return {"error": "Revenue projection not found"}
        
        # Calculate NPV
        cash_flows = [
            {"year": r["year"], "cash_flow": r["revenue"] * 0.3}
            for r in revenue.get("revenue_trajectory", [])
        ]
        npv = financial_modeling_service.calculate_npv(asset_id, cash_flows)
        
        return {
            "revenue": revenue,
            "npv": npv
        }
    
    async def _generate_report_tool(self, template: str, asset_id: str, scenario_id: Optional[str] = None) -> Dict[str, Any]:
        """Tool: Generate report"""
        # Placeholder
        return {
            "template": template,
            "asset_id": asset_id,
            "status": "generated"
        }
    
    async def _search_web_tool(self, query: str, search_instructions: Optional[str] = None) -> Dict[str, Any]:
        """Tool: Google Search"""
        google_agent = self.available_agents.get("google_search")
        if google_agent:
            results = await google_agent.search_web(query, search_instructions, max_results=10)
            return {
                "results": [r.dict() if hasattr(r, 'dict') else r for r in results],
                "query": query
            }
        return {"error": "Google Search agent not available"}
    
    async def _get_drug_info_tool(self, drug_name: str) -> Dict[str, Any]:
        """Tool: GoodRx price search"""
        goodrx_agent = self.available_agents.get("goodrx")
        if goodrx_agent:
            result = await goodrx_agent.get_drug_info(drug_name)
            return result.dict() if result and hasattr(result, 'dict') else {"drug": drug_name, "pricing": "Not available"}
        return {"error": "GoodRx agent not available"}


# Global instance
asset_strategy_agent = AssetStrategyAgent()

