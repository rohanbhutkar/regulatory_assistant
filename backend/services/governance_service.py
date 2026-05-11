"""
Governance Service - Approval routing, audit trail, decision records
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


class GovernanceService:
    """Service for governance and audit"""
    
    def __init__(self):
        # In-memory storage
        self._audit_log: List[Dict[str, Any]] = []
        self._decision_records: Dict[str, Dict[str, Any]] = {}
        self._approval_chains: Dict[str, Dict[str, Any]] = {}
    
    def log_event(
        self,
        event_type: str,
        user_id: str,
        asset_id: Optional[str] = None,
        report_id: Optional[str] = None,
        details: Dict[str, Any] = None
    ):
        """Log an audit event"""
        event = {
            "id": str(uuid.uuid4()),
            "event_type": event_type,
            "user_id": user_id,
            "asset_id": asset_id,
            "report_id": report_id,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        self._audit_log.append(event)
        return event
    
    def create_decision_record(
        self,
        asset_id: str,
        report_id: str,
        scenario_id: Optional[str] = None,
        decision_cut_id: Optional[str] = None,
        decision: str = "go",
        rationale: str = ""
    ) -> Dict[str, Any]:
        """Create a decision record"""
        record_id = str(uuid.uuid4())
        
        record = {
            "id": record_id,
            "asset_id": asset_id,
            "report_id": report_id,
            "scenario_id": scenario_id,
            "decision_cut_id": decision_cut_id,
            "decision": decision,
            "rationale": rationale,
            "created_at": datetime.now().isoformat(),
            "immutable": True
        }
        
        self._decision_records[record_id] = record
        self.log_event("decision_recorded", "system", asset_id=asset_id, report_id=report_id)
        
        return record
    
    def get_audit_trail(
        self,
        asset_id: Optional[str] = None,
        report_id: Optional[str] = None,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get audit trail with optional filtering"""
        events = self._audit_log
        
        if asset_id:
            events = [e for e in events if e.get("asset_id") == asset_id]
        if report_id:
            events = [e for e in events if e.get("report_id") == report_id]
        if event_type:
            events = [e for e in events if e.get("event_type") == event_type]
        
        return events


# Global instance
governance_service = GovernanceService()


