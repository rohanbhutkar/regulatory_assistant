"""
Reporting API Routes - Module 8: Reporting, Outputs & Governance
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from datetime import datetime
from services.report_generation_service import report_generation_service
from services.governance_service import governance_service

router = APIRouter()


@router.get("/templates")
async def list_templates():
    """List available report templates"""
    templates = report_generation_service.list_templates()
    return {"templates": templates}


@router.post("/generate")
async def generate_report(
    template_name: str,
    asset_id: str,
    scenario_id: Optional[str] = None,
    decision_cut_id: Optional[str] = None,
    markets: Optional[List[str]] = None,
    generated_by: str = "user_001"
):
    """Generate a report"""
    report = report_generation_service.generate_report(
        template_name=template_name,
        asset_id=asset_id,
        scenario_id=scenario_id,
        decision_cut_id=decision_cut_id,
        markets=markets,
        generated_by=generated_by
    )
    
    # Log event
    governance_service.log_event(
        "report_generated",
        generated_by,
        asset_id=asset_id,
        report_id=report["id"]
    )
    
    return report


@router.get("/{report_id}")
async def get_report(report_id: str):
    """Get report details"""
    report = report_generation_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/{report_id}/preview")
async def preview_report(report_id: str):
    """Preview report"""
    report = report_generation_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # In real implementation, would render template with data
    return {
        "report_id": report_id,
        "preview": "Report preview would be rendered here"
    }


@router.post("/{report_id}/export")
async def export_report(
    report_id: str,
    format: str = "pdf"  # pdf, ppt, excel
):
    """Export report in specified format"""
    report = report_generation_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # In real implementation, would generate PDF/PPT/Excel
    return {
        "report_id": report_id,
        "format": format,
        "file_path": f"exports/{report_id}.{format}",
        "exported_at": datetime.now().isoformat()
    }


@router.post("/{report_id}/approve")
async def request_report_approval(
    report_id: str,
    required_approvers: List[str],
    requester_id: str = "user_001"
):
    """Request approval for a report"""
    # Log event
    governance_service.log_event(
        "report_approval_requested",
        requester_id,
        report_id=report_id
    )
    
    return {
        "report_id": report_id,
        "status": "pending_approval",
        "required_approvers": required_approvers
    }


@router.get("/{report_id}/regenerate")
async def regenerate_report(report_id: str):
    """Regenerate report from stored parameters"""
    report = report_generation_service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Regenerate with same parameters
    new_report = report_generation_service.generate_report(
        template_name=report["template_name"],
        asset_id=report["asset_id"],
        scenario_id=report.get("scenario_id"),
        decision_cut_id=report.get("decision_cut_id"),
        markets=report.get("markets"),
        generated_by="system"
    )
    
    return new_report


@router.get("/audit-trail")
async def get_audit_trail(
    asset_id: Optional[str] = None,
    report_id: Optional[str] = None,
    event_type: Optional[str] = None
):
    """Get audit trail"""
    events = governance_service.get_audit_trail(
        asset_id=asset_id,
        report_id=report_id,
        event_type=event_type
    )
    return {"events": events}

