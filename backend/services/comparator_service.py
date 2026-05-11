"""
Comparator Service - Manages comparators and coverage information
"""
from typing import List, Dict, Any, Optional
import pandas as pd
from utils.optimized_data_loader import OptimizedDataLoader


class ComparatorService:
    """Service for managing comparators and recommendations"""
    
    def __init__(self):
        self.stored_comparators: Dict[str, List[Dict[str, Any]]] = {}
    
    def store_comparators(self, asset_id: str, comparators: List[Dict[str, Any]]):
        """Store AI-generated comparators in memory"""
        self.stored_comparators[asset_id] = comparators
    
    def get_stored_comparators(self, asset_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get stored comparators for an asset"""
        return self.stored_comparators.get(asset_id)
    
    def recommend_comparators(
        self,
        asset_id: str,
        indication: str,
        market: str,
        therapeutic_area: Optional[str] = None,
        moa: Optional[str] = None,
        loader: Optional[OptimizedDataLoader] = None
    ) -> List[Dict[str, Any]]:
        """Recommend comparators for an asset"""
        # First check for stored comparators (from AI generation)
        stored = self.get_stored_comparators(asset_id)
        if stored:
            return stored
        
        # Fallback to data source search if no stored comparators
        recommendations = []
        
        if not loader:
            return recommendations
        
        # Search in various data sources
        try:
            # Search TrialTrove for similar trials
            from agents.trialtrove_agent import TrialTroveAgent
            trialtrove_agent = TrialTroveAgent(loader)
            trials = trialtrove_agent.search_studies(
                indication=indication,
                therapeutic_area=therapeutic_area
            )
            
            # Extract comparator drugs from trials
            for trial in trials[:10]:  # Limit to top 10
                if 'interventions' in trial:
                    for intervention in trial['interventions']:
                        if intervention.get('type') == 'Drug':
                            recommendations.append({
                                "drug": intervention.get('name', 'Unknown'),
                                "indication": indication,
                                "rationale": f"Found in clinical trial: {trial.get('title', '')[:100]}",
                                "market": market,
                                "similarity_score": 0.7
                            })
        except Exception:
            pass  # Silently fail if data source unavailable
        
        # Sort by similarity score
        recommendations.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)
        
        return recommendations
    
    def _get_coverage_info(self, drug_name: str, loader: OptimizedDataLoader, indication: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get coverage information for a drug from formulary data using multiple matching strategies"""
        # Use unified PayerDataService for matching
        try:
            from services.payer_data_service import payer_data_service
            payer_data_service.data_loader = loader
            
            coverage = payer_data_service.get_formulary_coverage(drug_name, indication)
            if coverage:
                # Return in expected format (remove internal fields)
                return {
                    "coverage_level": coverage.get("coverage_level"),
                    "tier": coverage.get("tier"),
                    "restrictions": coverage.get("restrictions", []),
                    "coverage_distribution": coverage.get("coverage_distribution", {})
                }
            
            return None
        except Exception:
            # Fallback: return default if service unavailable
            return {
                "coverage_level": "Not Listed/Unknown",
                "tier": "Unknown",
                "restrictions": [],
                "coverage_distribution": {
                    "Unrestricted": 0.0,
                    "Restricted": 0.0,
                    "Not Covered": 0.0,
                    "Not Listed/Unknown": 100.0
                }
            }


# Singleton instance
comparator_service = ComparatorService()
