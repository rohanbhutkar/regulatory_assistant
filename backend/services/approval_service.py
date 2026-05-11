"""
Approval Service - Approval workflow engine
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
from models.asset_strategy_models import (
    Approval, ApprovalRequest, ApprovalStatus,
    ApproveDecisionCutRequest, RejectDecisionCutRequest
)
from services.decision_cut_service import decision_cut_service


class ApprovalService:
    """Service for managing approval workflows"""
    
    def __init__(self):
        # In-memory storage
        self._approvals: Dict[str, Approval] = {}
        self._cut_approvals: Dict[str, List[str]] = {}  # cut_id -> list of approval IDs
        self._approval_chains: Dict[str, Dict[str, Any]] = {}  # asset_id or TA -> approval chain config
    
    def request_approval(self, request: ApprovalRequest, requester_id: str) -> List[Approval]:
        """Request approval for a decision cut"""
        # Verify decision cut exists
        cut = decision_cut_service.get_decision_cut(request.decision_cut_id)
        if not cut:
            raise ValueError(f"Decision cut {request.decision_cut_id} not found")
        
        # Create approval records for each required approver
        approvals = []
        for approver_id in request.required_approvers:
            approval = Approval(
                id=str(uuid.uuid4()),
                decision_cut_id=request.decision_cut_id,
                approver_id=approver_id,
                status=ApprovalStatus.PENDING,
                comments=None
            )
            self._approvals[approval.id] = approval
            approvals.append(approval)
            
            # Track by cut
            if request.decision_cut_id not in self._cut_approvals:
                self._cut_approvals[request.decision_cut_id] = []
            self._cut_approvals[request.decision_cut_id].append(approval.id)
        
        # Update decision cut status
        decision_cut_service.update_decision_cut_status(request.decision_cut_id, "pending_approval")
        
        return approvals
    
    def approve(self, request: ApproveDecisionCutRequest, approver_id: str) -> Optional[Approval]:
        """Approve a decision cut"""
        approval = self._approvals.get(request.approval_id)
        if not approval:
            return None
        
        # Verify approver matches
        if approval.approver_id != approver_id:
            raise ValueError("Approver ID does not match")
        
        # Update approval
        approval.status = ApprovalStatus.APPROVED
        approval.comments = request.comments
        approval.approved_at = datetime.now().isoformat()
        self._approvals[request.approval_id] = approval
        
        # Check if all required approvals are complete
        cut_id = approval.decision_cut_id
        all_approvals = self.get_approvals_for_cut(cut_id)
        required_approvals = [a for a in all_approvals if a.status != ApprovalStatus.DELEGATED]
        
        if all(a.status == ApprovalStatus.APPROVED for a in required_approvals):
            # All approved - update decision cut status
            decision_cut_service.update_decision_cut_status(cut_id, "approved")
        
        return approval
    
    def reject(self, request: RejectDecisionCutRequest, approver_id: str) -> Optional[Approval]:
        """Reject a decision cut"""
        approval = self._approvals.get(request.approval_id)
        if not approval:
            return None
        
        # Verify approver matches
        if approval.approver_id != approver_id:
            raise ValueError("Approver ID does not match")
        
        # Update approval
        approval.status = ApprovalStatus.REJECTED
        approval.comments = request.comments
        approval.approved_at = datetime.now().isoformat()
        self._approvals[request.approval_id] = approval
        
        # Update decision cut status back to draft
        decision_cut_service.update_decision_cut_status(approval.decision_cut_id, "draft")
        
        return approval
    
    def delegate(self, approval_id: str, delegate_to_id: str, delegator_id: str) -> Optional[Approval]:
        """Delegate approval to another reviewer"""
        approval = self._approvals.get(approval_id)
        if not approval:
            return None
        
        # Verify delegator matches
        if approval.approver_id != delegator_id:
            raise ValueError("Delegator ID does not match")
        
        # Create new approval for delegate
        new_approval = Approval(
            id=str(uuid.uuid4()),
            decision_cut_id=approval.decision_cut_id,
            approver_id=delegate_to_id,
            status=ApprovalStatus.PENDING,
            comments=None
        )
        self._approvals[new_approval.id] = new_approval
        
        # Mark original as delegated
        approval.status = ApprovalStatus.DELEGATED
        approval.comments = f"Delegated to {delegate_to_id}"
        self._approvals[approval_id] = approval
        
        # Track by cut
        cut_id = approval.decision_cut_id
        if cut_id not in self._cut_approvals:
            self._cut_approvals[cut_id] = []
        self._cut_approvals[cut_id].append(new_approval.id)
        
        return new_approval
    
    def get_approvals_for_cut(self, cut_id: str) -> List[Approval]:
        """Get all approvals for a decision cut"""
        approval_ids = self._cut_approvals.get(cut_id, [])
        approvals = [self._approvals[aid] for aid in approval_ids if aid in self._approvals]
        return approvals
    
    def get_pending_approvals(self, approver_id: Optional[str] = None) -> List[Approval]:
        """Get pending approvals (optionally filtered by approver)"""
        pending = [
            a for a in self._approvals.values()
            if a.status == ApprovalStatus.PENDING
        ]
        
        if approver_id:
            pending = [a for a in pending if a.approver_id == approver_id]
        
        return pending
    
    def define_approval_chain(
        self,
        asset_id: Optional[str] = None,
        therapeutic_area: Optional[str] = None,
        chain_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Define approval chain configuration"""
        key = asset_id or therapeutic_area or "default"
        self._approval_chains[key] = chain_config
        return chain_config
    
    def get_approval_chain(
        self,
        asset_id: Optional[str] = None,
        therapeutic_area: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get approval chain configuration"""
        # Try asset-specific first, then TA, then default
        if asset_id and asset_id in self._approval_chains:
            return self._approval_chains[asset_id]
        if therapeutic_area and therapeutic_area in self._approval_chains:
            return self._approval_chains[therapeutic_area]
        return self._approval_chains.get("default")


# Global instance
approval_service = ApprovalService()


