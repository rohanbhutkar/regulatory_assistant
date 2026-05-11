"""
HTA Intelligence Service - HTA outcome prediction, comparator ranking, evidence gap analysis
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import numpy as np
from utils.optimized_data_loader import OptimizedDataLoader


class HTAIntelligenceService:
    """Service for HTA intelligence and market access predictions"""
    
    def __init__(self, data_loader: Optional[OptimizedDataLoader] = None):
        # In-memory storage
        self._hta_assessments: Dict[str, Dict[str, Any]] = {}
        self.data_loader = data_loader
        self._market_playbooks: Dict[str, Dict[str, Any]] = {
            "CN": {
                "hta_body": "NMPA",
                "typical_timeline_months": 12,
                "decision_criteria": ["efficacy", "safety", "cost_effectiveness"]
            },
            "DE": {
                "hta_body": "G-BA",
                "typical_timeline_months": 18,
                "decision_criteria": ["benefit_assessment", "cost_benefit", "comparator"]
            },
            "JP": {
                "hta_body": "MHLW",
                "typical_timeline_months": 12,
                "decision_criteria": ["efficacy", "safety", "pricing"]
            }
        }
    
    def get_hta_pathway(
        self,
        asset_id: str,
        market: str
    ) -> Dict[str, Any]:
        """Get HTA pathway timeline and requirements for a market"""
        playbook = self._market_playbooks.get(market, {})
        
        pathway = {
            "market": market,
            "hta_body": playbook.get("hta_body", "Unknown"),
            "steps": [
                {
                    "step": "Submission",
                    "duration_months": 1,
                    "required_inputs": ["protocol", "efficacy_data", "safety_data"]
                },
                {
                    "step": "Review",
                    "duration_months": playbook.get("typical_timeline_months", 12) - 2,
                    "required_inputs": ["comparator_analysis", "cost_effectiveness"]
                },
                {
                    "step": "Decision",
                    "duration_months": 1,
                    "required_inputs": []
                },
                {
                    "step": "Reimbursement",
                    "duration_months": 2,
                    "required_inputs": ["price_negotiation"]
                }
            ],
            "total_timeline_months": playbook.get("typical_timeline_months", 12)
        }
        
        return pathway
    
    def predict_hta_outcome_likelihood(
        self,
        asset_id: str,
        market: str,
        evidence_strength: float = 0.5,
        comparator_clarity: float = 0.5,
        precedent_strength: float = 0.5,
        policy_environment: str = "moderate"
    ) -> Dict[str, Any]:
        """
        Predict HTA outcome likelihood
        
        P(outcome_i | evidence, precedents, comparators) = f(evidence_strength, precedent_match, comparator_fit, policy_environment)
        """
        # Simplified prediction model
        # In real implementation, would use ML model or rule-based system
        
        # Base probabilities
        base_approval = 0.4
        base_restriction = 0.4
        base_rejection = 0.2
        
        # Adjust based on evidence strength
        evidence_adjustment = (evidence_strength - 0.5) * 0.3
        base_approval += evidence_adjustment
        base_rejection -= evidence_adjustment
        
        # Adjust based on comparator clarity
        comparator_adjustment = (comparator_clarity - 0.5) * 0.2
        base_approval += comparator_adjustment
        base_restriction -= comparator_adjustment
        
        # Adjust based on precedent strength
        precedent_adjustment = (precedent_strength - 0.5) * 0.2
        base_approval += precedent_adjustment
        
        # Adjust for policy environment
        if policy_environment == "progressive":
            base_approval += 0.1
        elif policy_environment == "conservative":
            base_approval -= 0.1
            base_restriction += 0.1
        
        # Normalize to ensure probabilities sum to 1
        total = base_approval + base_restriction + base_rejection
        base_approval /= total
        base_restriction /= total
        base_rejection /= total
        
        outcome_likelihood = {
            "approval": float(base_approval),
            "restriction": float(base_restriction),
            "rejection": float(base_rejection)
        }
        
        # Calculate confidence
        confidence = min(evidence_strength, comparator_clarity, precedent_strength)
        
        # Store assessment
        key = f"{asset_id}_{market}"
        self._hta_assessments[key] = {
            "asset_id": asset_id,
            "market": market,
            "outcome_likelihood": outcome_likelihood,
            "confidence": confidence,
            "assessed_at": datetime.now().isoformat()
        }
        
        return {
            "outcome_likelihood": outcome_likelihood,
            "confidence": float(confidence),
            "evidence_strength": evidence_strength,
            "comparator_clarity": comparator_clarity,
            "precedent_strength": precedent_strength
        }
    
    def rank_comparators(
        self,
        asset_id: str,
        comparators: List[Dict[str, Any]],
        indication: str,
        market: str,
        loader: Optional[OptimizedDataLoader] = None
    ) -> List[Dict[str, Any]]:
        """
        Rank comparators by likelihood of being used in HTA
        
        Score(comp_j) = w1*GuidelineMatch + w2*PrecedentFrequency + w3*SoCFit + w4*ExpertOverride
        """
        ranked = []
        
        for comp in comparators:
            drug = comp.get("drug", "")
            
            # Guideline match (simplified - would check actual guidelines)
            guideline_match = 0.5  # Placeholder
            
            # Precedent frequency (check TrialTrove)
            precedent_frequency = 0.0
            if loader:
                trial_df = loader.get_data('trialtrove')
                if not trial_df.empty:
                    matches = trial_df[
                        (trial_df.get('Primary Tested Drug', '').str.contains(drug, case=False, na=False)) &
                        (trial_df.get('Disease', '').str.contains(indication, case=False, na=False))
                    ]
                    precedent_frequency = min(len(matches) / 10.0, 1.0)  # Normalize
            
            # SoC fit (simplified)
            soc_fit = 0.5  # Placeholder
            
            # Expert override
            expert_override = comp.get("expert_override", 0.0)
            
            # Calculate score
            score = (
                0.3 * guideline_match +
                0.3 * precedent_frequency +
                0.3 * soc_fit +
                0.1 * expert_override
            ) * 100
            
            ranked.append({
                **comp,
                "likelihood_score": float(score),
                "breakdown": {
                    "guideline_match": guideline_match * 100,
                    "precedent_frequency": precedent_frequency * 100,
                    "soc_fit": soc_fit * 100,
                    "expert_override": expert_override * 100
                }
            })
        
        # Sort by score
        ranked.sort(key=lambda x: x.get("likelihood_score", 0), reverse=True)
        
        return ranked
    
    def predict_time_to_reimbursement(
        self,
        asset_id: str,
        market: str,
        evidence_completeness: float = 0.5,
        comparator_clarity: float = 0.5
    ) -> Dict[str, Any]:
        """Predict time-to-reimbursement by market"""
        playbook = self._market_playbooks.get(market, {})
        base_timeline = playbook.get("typical_timeline_months", 12)
        
        # Adjust based on evidence completeness
        evidence_adjustment = (1 - evidence_completeness) * 6  # Up to 6 months delay
        comparator_adjustment = (1 - comparator_clarity) * 3  # Up to 3 months delay
        
        predicted_months = base_timeline + evidence_adjustment + comparator_adjustment
        
        # Calculate percentiles (simplified)
        p10 = predicted_months * 0.8
        p50 = predicted_months
        p90 = predicted_months * 1.3
        
        return {
            "time_to_reimbursement_months": int(predicted_months),
            "p10": int(p10),
            "p50": int(p50),
            "p90": int(p90),
            "base_timeline": base_timeline,
            "adjustments": {
                "evidence_delay": evidence_adjustment,
                "comparator_delay": comparator_adjustment
            }
        }
    
    def calculate_access_risk(
        self,
        asset_id: str,
        market: str,
        endpoint_maturity: float = 0.5,
        comparator_clarity: float = 0.5,
        precedent_strength: float = 0.5,
        policy_uncertainty: float = 0.5,
        price_aggressiveness: float = 0.5
    ) -> Dict[str, Any]:
        """
        Calculate access risk score (0-100)
        
        AccessRisk = f(endpoint_maturity, comparator_clarity, precedent_strength, policy_uncertainty, price_aggressiveness)
        """
        # Weighted risk components
        endpoint_risk = (1 - endpoint_maturity) * 25  # 0-25 points
        comparator_risk = (1 - comparator_clarity) * 20  # 0-20 points
        precedent_risk = (1 - precedent_strength) * 20  # 0-20 points
        policy_risk = policy_uncertainty * 20  # 0-20 points
        price_risk = price_aggressiveness * 15  # 0-15 points
        
        total_risk = endpoint_risk + comparator_risk + precedent_risk + policy_risk + price_risk
        
        return {
            "access_risk_score": float(total_risk),
            "breakdown": {
                "endpoint_maturity": {
                    "score": float(endpoint_risk),
                    "max": 25,
                    "maturity": endpoint_maturity
                },
                "comparator_clarity": {
                    "score": float(comparator_risk),
                    "max": 20,
                    "clarity": comparator_clarity
                },
                "precedent_strength": {
                    "score": float(precedent_risk),
                    "max": 20,
                    "strength": precedent_strength
                },
                "policy_uncertainty": {
                    "score": float(policy_risk),
                    "max": 20,
                    "uncertainty": policy_uncertainty
                },
                "price_aggressiveness": {
                    "score": float(price_risk),
                    "max": 15,
                    "aggressiveness": price_aggressiveness
                }
            }
        }
    
    def analyze_evidence_gaps(
        self,
        asset_id: str,
        market: str,
        required_evidence: List[str],
        available_evidence: List[str]
    ) -> Dict[str, Any]:
        """Analyze evidence gaps and their impact on HTA outcome"""
        gaps = []
        available_set = set(available_evidence)
        
        for req in required_evidence:
            status = "available" if req in available_set else "missing"
            partial = False
            
            # Check for partial matches
            if status == "missing":
                for avail in available_evidence:
                    if req.lower() in avail.lower() or avail.lower() in req.lower():
                        status = "partial"
                        partial = True
                        break
            
            gaps.append({
                "required_evidence": req,
                "status": status,
                "impact": "high" if status == "missing" else ("medium" if partial else "low")
            })
        
        # Calculate gap impact
        missing_count = sum(1 for g in gaps if g["status"] == "missing")
        partial_count = sum(1 for g in gaps if g["status"] == "partial")
        
        return {
            "gaps": gaps,
            "summary": {
                "total_required": len(required_evidence),
                "available": len(available_evidence),
                "missing": missing_count,
                "partial": partial_count
            },
            "impact_on_outcome": {
                "approval_likelihood_reduction": missing_count * 0.1 + partial_count * 0.05
            }
        }
    
    def get_hta_assessment(self, asset_id: str, market: str) -> Optional[Dict[str, Any]]:
        """Get stored HTA assessment"""
        key = f"{asset_id}_{market}"
        return self._hta_assessments.get(key)
    
    def get_country_specifications(self, country: str) -> Dict[str, Any]:
        """
        Get country-specific specifications from CPP data
        
        Useful for market-specific HTA rules and adjustments
        """
        if not self.data_loader:
            return {}
        
        country_specs_df = self.data_loader.get_cpp_data('country_specs')
        if country_specs_df.empty:
            return {}
        
        # Filter by country (column name may vary)
        country_col = None
        for col in country_specs_df.columns:
            if 'country' in col.lower():
                country_col = col
                break
        
        if country_col:
            country_matches = country_specs_df[country_specs_df[country_col].str.contains(country, case=False, na=False)]
            if not country_matches.empty:
                return {
                    "country": country,
                    "specifications": country_matches.to_dict('records'),
                    "data_source": "cpp_country_specs",
                    "rationale": f"Country-specific rules and adjustments for {country}"
                }
        
        return {}
    
    def get_indication_rules(self, indication: str) -> Dict[str, Any]:
        """
        Get indication-specific rules from CPP data
        
        Useful for therapeutic area-specific HTA considerations
        """
        if not self.data_loader:
            return {}
        
        indications_df = self.data_loader.get_cpp_data('indications')
        if indications_df.empty:
            return {}
        
        # Filter by indication (fuzzy matching would be ideal)
        indication_col = None
        for col in indications_df.columns:
            if 'indication' in col.lower() or 'disease' in col.lower():
                indication_col = col
                break
        
        if indication_col:
            indication_matches = indications_df[indications_df[indication_col].str.contains(indication, case=False, na=False)]
            if not indication_matches.empty:
                return {
                    "indication": indication,
                    "rules": indication_matches.to_dict('records'),
                    "data_source": "cpp_indications",
                    "rationale": f"Indication-specific rules for {indication}"
                }
        
        return {}


# Global instance (will be initialized with data_loader in main_complete)
hta_intelligence_service = HTAIntelligenceService()

