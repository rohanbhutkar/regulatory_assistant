"""
Report Generation Service - Generate PDF/PPT/Excel reports
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


class ReportGenerationService:
    """Service for generating reports"""
    
    def __init__(self):
        # In-memory storage
        self._reports: Dict[str, Dict[str, Any]] = {}
        self._templates = {
            "early_opportunity_assessment": {
                "name": "Early Opportunity Assessment",
                "sections": [
                    "executive_summary",
                    "asset_overview",
                    "market_opportunity",
                    "price_potential",
                    "hta_outlook",
                    "financial_value",
                    "risks_mitigations",
                    "evidence_summary",
                    "assumptions"
                ]
            },
            "pricing_benchmark_handout": {
                "name": "Pricing Benchmark Handout",
                "sections": [
                    "price_waterfall",
                    "comparator_table",
                    "price_positioning",
                    "subpopulation_potential",
                    "confidence_coverage"
                ]
            },
            "hta_access_outlook": {
                "name": "HTA Access Outlook",
                "sections": [
                    "hta_pathway_timeline",
                    "outcome_likelihood",
                    "comparator_recommendations",
                    "evidence_gaps",
                    "access_risk",
                    "time_to_reimbursement"
                ]
            },
            "scenario_sensitivity_pack": {
                "name": "Scenario Sensitivity Pack",
                "sections": [
                    "scenario_comparison",
                    "key_metrics",
                    "sensitivity_analysis",
                    "monte_carlo_results",
                    "assumption_differences",
                    "recommendations"
                ]
            },
            "executive_onepager": {
                "name": "Executive One-Pager",
                "sections": [
                    "key_metrics",
                    "price_corridor",
                    "hta_outlook",
                    "top_risks",
                    "recommendation"
                ]
            }
        }
    
    def generate_report(
        self,
        template_name: str,
        asset_id: str,
        scenario_id: Optional[str] = None,
        decision_cut_id: Optional[str] = None,
        markets: List[str] = None,
        generated_by: str = "system"
    ) -> Dict[str, Any]:
        """Generate a report"""
        template = self._templates.get(template_name)
        if not template:
            raise ValueError(f"Template {template_name} not found")
        
        report_id = str(uuid.uuid4())
        
        report = {
            "id": report_id,
            "template_name": template_name,
            "template": template,
            "asset_id": asset_id,
            "scenario_id": scenario_id,
            "decision_cut_id": decision_cut_id,
            "markets": markets or ["US"],
            "generated_at": datetime.now().isoformat(),
            "generated_by": generated_by,
            "data_versions": {
                "trialtrove": datetime.now().isoformat(),
                "payer_data": datetime.now().isoformat()
            },
            "status": "generated"
        }
        
        self._reports[report_id] = report
        return report
    
    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get report by ID"""
        return self._reports.get(report_id)
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List available report templates"""
        return [
            {"id": k, **v}
            for k, v in self._templates.items()
        ]


# Global instance
report_generation_service = ReportGenerationService()


