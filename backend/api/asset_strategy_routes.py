"""
Asset Strategy API Routes - Phase 1: Asset & Portfolio Management Core
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from typing import List, Dict, Any, Optional
from models.asset_strategy_models import (
    AssetStrategy, CreateAssetRequest, UpdateAssetRequest,
    DecisionCut, CreateDecisionCutRequest, DecisionCutDiff,
    Approval, ApprovalRequest, ApproveDecisionCutRequest, RejectDecisionCutRequest,
    EvidenceArtifact, AssumptionSet, CreateAssumptionSetRequest, UpdateAssumptionSetRequest, Comparator
)
from services.asset_management_service import asset_management_service
from services.decision_cut_service import decision_cut_service
from services.approval_service import approval_service
from services.evidence_artifact_service import evidence_artifact_service
from services.assumption_set_service import assumption_set_service
from utils.optimized_data_loader import OptimizedDataLoader

router = APIRouter()

# Test endpoint to verify route registration
@router.get("/test")
async def test_route():
    """Test endpoint to verify route registration"""
    return {"message": "Asset strategy routes are working", "total_assets": len(asset_management_service._assets)}

# Debug endpoint to list all assets
@router.get("/debug/assets")
async def debug_list_all_assets():
    """Debug endpoint to list all asset IDs"""
    return {
        "total": len(asset_management_service._assets),
        "asset_ids": list(asset_management_service._assets.keys())[:20],
        "asset-1_exists": "asset-1" in asset_management_service._assets,
        "service_initialized": asset_management_service._initialized
    }

# Global data loader reference (will be set by main_complete)
_data_loader: Optional[OptimizedDataLoader] = None

def set_data_loader(loader: OptimizedDataLoader):
    """Set the data loader instance (called from main_complete)"""
    global _data_loader
    _data_loader = loader

def get_data_loader() -> OptimizedDataLoader:
    """Get data loader instance"""
    global _data_loader
    if _data_loader is None:
        # Fallback to creating new instance
        from utils.optimized_data_loader import OptimizedDataLoader
        _data_loader = OptimizedDataLoader()
        # Load essential data
        import asyncio
        try:
            asyncio.run(_data_loader.load_essential_data())
        except:
            pass
    return _data_loader

# Mock user ID (in real implementation, get from auth)
def get_current_user_id() -> str:
    """Get current user ID from auth context"""
    return "user_001"  # Placeholder

# Initialize assets from TrialTrove on first request
_assets_initialized = False


# Asset CRUD endpoints
@router.get("/assets", response_model=List[AssetStrategy])
async def list_assets(
    therapeutic_area: Optional[List[str]] = None,
    development_stage: Optional[List[str]] = None,
    status: Optional[List[str]] = None,
    indication: Optional[List[str]] = None,
    sort_by: str = "asset_name",
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 50,
    loader: OptimizedDataLoader = Depends(get_data_loader)
):
    """List assets with filtering and sorting"""
    global _assets_initialized
    # Initialize from TrialTrove on first request
    # Check service's initialization status, not just the module flag
    if not _assets_initialized or not asset_management_service._initialized:
        count = asset_management_service.initialize_from_trialtrove(loader)
        _assets_initialized = True
        print(f"Initialized {count} assets from mock and TrialTrove")
    
    filters = {}
    if therapeutic_area:
        filters["therapeutic_area"] = therapeutic_area
    if development_stage:
        filters["development_stage"] = development_stage
    if status:
        filters["status"] = status
    if indication:
        filters["indication"] = indication
    
    assets, total_count = asset_management_service.list_assets(
        filters=filters if filters else None,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size
    )
    
    return assets


@router.post("/assets", response_model=AssetStrategy)
async def create_asset(
    request: CreateAssetRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new asset"""
    asset = asset_management_service.create_asset(request, created_by=user_id)
    return asset


@router.get("/assets/{asset_id}", response_model=AssetStrategy)
async def get_asset(asset_id: str, loader: OptimizedDataLoader = Depends(get_data_loader)):
    """Get asset details"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"🚀 GET /assets/{asset_id} - Route handler called")
    
    try:
        global _assets_initialized
        # Initialize from TrialTrove on first request if needed (fallback if not initialized at startup)
        # Check service's initialization status, not just the module flag
        if not _assets_initialized or not asset_management_service._initialized:
            logger.info("Initializing assets from mock and TrialTrove...")
            count = asset_management_service.initialize_from_trialtrove(loader)
            _assets_initialized = True
            logger.info(f"Initialized {count} assets from mock and TrialTrove (lazy init)")
        
        # Debug logging
        logger.info(f"🔍 Looking for asset_id: '{asset_id}'")
        logger.info(f"📊 Total assets in service: {len(asset_management_service._assets)}")
        logger.info(f"📋 First 10 asset IDs: {list(asset_management_service._assets.keys())[:10]}")
        
        asset = asset_management_service.get_asset(asset_id)
        if not asset:
            available_ids = list(asset_management_service._assets.keys())[:10]
            error_msg = f"Asset '{asset_id}' not found. Available assets (first 10): {available_ids}. Total assets: {len(asset_management_service._assets)}"
            logger.error(f"❌ {error_msg}")
            raise HTTPException(status_code=404, detail=error_msg)
        
        logger.info(f"✅ Found asset: {asset.asset_name}")
        return asset
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in get_asset: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.put("/assets/{asset_id}", response_model=AssetStrategy)
async def update_asset(
    asset_id: str,
    request: UpdateAssetRequest
):
    """Update an asset"""
    asset = asset_management_service.update_asset(asset_id, request)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.delete("/assets/{asset_id}")
async def delete_asset(asset_id: str):
    """Delete an asset (soft delete)"""
    success = asset_management_service.delete_asset(asset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"message": "Asset deleted successfully"}


# Decision Cut endpoints
@router.get("/assets/{asset_id}/decision-cuts", response_model=List[DecisionCut])
async def list_decision_cuts(asset_id: str):
    """List all decision cuts for an asset"""
    cuts = decision_cut_service.list_decision_cuts(asset_id)
    return cuts


@router.post("/assets/{asset_id}/decision-cuts", response_model=DecisionCut)
async def create_decision_cut(
    asset_id: str,
    request: CreateDecisionCutRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Create a new decision cut"""
    # Override asset_id from path
    request.asset_id = asset_id
    cut = decision_cut_service.create_decision_cut(request, frozen_by=user_id)
    
    # Auto-request approval if required approvers specified
    if request.required_approvers:
        approval_request = ApprovalRequest(
            decision_cut_id=cut.id,
            required_approvers=request.required_approvers,
            notes=request.notes
        )
        approval_service.request_approval(approval_request, requester_id=user_id)
    
    return cut


@router.get("/decision-cuts/{cut_id}", response_model=DecisionCut)
async def get_decision_cut(cut_id: str):
    """Get decision cut details"""
    cut = decision_cut_service.get_decision_cut(cut_id)
    if not cut:
        raise HTTPException(status_code=404, detail="Decision cut not found")
    return cut


@router.get("/decision-cuts/{cut_id}/diff", response_model=DecisionCutDiff)
async def compare_decision_cuts(cut_id: str, compare_with: str):
    """Compare two decision cuts"""
    diff = decision_cut_service.compare_decision_cuts(cut_id, compare_with)
    return diff


# Approval endpoints
@router.get("/assets/{asset_id}/approvals", response_model=List[Approval])
async def list_approvals(asset_id: str):
    """List approvals for an asset (via decision cuts)"""
    cuts = decision_cut_service.list_decision_cuts(asset_id)
    all_approvals = []
    for cut in cuts:
        approvals = approval_service.get_approvals_for_cut(cut.id)
        all_approvals.extend(approvals)
    return all_approvals


@router.post("/assets/{asset_id}/approvals")
async def request_approval(
    asset_id: str,
    request: ApprovalRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Request approval for a decision cut"""
    approvals = approval_service.request_approval(request, requester_id=user_id)
    return {"approvals": approvals, "message": "Approval requested"}


@router.post("/approvals/{approval_id}/approve", response_model=Approval)
async def approve_decision_cut(
    approval_id: str,
    request: ApproveDecisionCutRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Approve a decision cut"""
    approval = approval_service.approve(request, approver_id=user_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@router.post("/approvals/{approval_id}/reject", response_model=Approval)
async def reject_decision_cut(
    approval_id: str,
    request: RejectDecisionCutRequest,
    user_id: str = Depends(get_current_user_id)
):
    """Reject a decision cut"""
    approval = approval_service.reject(request, approver_id=user_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


# Evidence endpoints
@router.get("/assets/{asset_id}/evidence", response_model=List[EvidenceArtifact])
async def list_evidence(
    asset_id: str,
    artifact_type: Optional[str] = None
):
    """List evidence artifacts for an asset"""
    from models.asset_strategy_models import EvidenceArtifactType
    evidence_type = EvidenceArtifactType(artifact_type) if artifact_type else None
    artifacts = evidence_artifact_service.list_artifacts(
        asset_id=asset_id,
        artifact_type=evidence_type
    )
    return artifacts


@router.post("/assets/{asset_id}/evidence", response_model=EvidenceArtifact)
async def upload_evidence(
    asset_id: str,
    file: Optional[UploadFile] = File(None),
    artifact_type: Optional[str] = None,
    user_id: str = Depends(get_current_user_id)
):
    """Upload an evidence artifact (supports both file upload and JSON body)"""
    from models.asset_strategy_models import EvidenceArtifactType
    from fastapi import Request
    import json
    
    # Check if request is JSON (for discovered evidence) or multipart (for file upload)
    # FastAPI will handle this automatically, but we need to support both
    
    # If file is provided, it's a file upload
    if file:
        file_path = f"uploads/{asset_id}/{file.filename}"
        artifact = evidence_artifact_service.upload_artifact(
            asset_id=asset_id,
            artifact_type=EvidenceArtifactType(artifact_type or "protocol"),
            file_name=file.filename,
            file_path=file_path,
            file_size=file.size if hasattr(file, 'size') else None,
            uploaded_by=user_id
        )
        return artifact
    else:
        # Handle JSON body for discovered evidence
        from fastapi import Body
        from typing import Dict, Any
        
        # This will be handled by a separate endpoint or we need to read the body
        # For now, create a route that accepts JSON
        raise HTTPException(
            status_code=400, 
            detail="Either file upload or JSON body with artifact details required. Use /assets/{asset_id}/evidence/json for JSON submissions."
        )


@router.post("/assets/{asset_id}/evidence/json", response_model=EvidenceArtifact)
async def create_evidence_from_json(
    asset_id: str,
    artifact_data: Dict[str, Any],
    user_id: str = Depends(get_current_user_id)
):
    """Create evidence artifact from JSON (for discovered evidence)"""
    from models.asset_strategy_models import EvidenceArtifactType
    
    artifact_type = artifact_data.get('artifact_type', 'protocol')
    file_name = artifact_data.get('file_name', 'Discovered Evidence')
    url = artifact_data.get('url')
    extracted_entities = artifact_data.get('extracted_entities', {})
    
    # Create artifact without file
    artifact = evidence_artifact_service.upload_artifact(
        asset_id=asset_id,
        artifact_type=EvidenceArtifactType(artifact_type),
        file_name=file_name,
        file_path=url or f"discovered/{asset_id}/{file_name}",
        file_size=None,
        uploaded_by=user_id
    )
    
    # Update with extracted entities if provided
    if extracted_entities:
        # In real implementation, would update artifact with entities
        pass
    
    return artifact


@router.get("/evidence/{artifact_id}", response_model=EvidenceArtifact)
async def get_evidence(artifact_id: str):
    """Get evidence artifact details"""
    artifact = evidence_artifact_service.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Evidence artifact not found")
    return artifact


@router.delete("/evidence/{artifact_id}")
async def delete_evidence(artifact_id: str):
    """Delete an evidence artifact"""
    success = evidence_artifact_service.delete_artifact(artifact_id)
    if not success:
        raise HTTPException(status_code=404, detail="Evidence artifact not found")
    return {"message": "Evidence artifact deleted successfully"}


# Assumption Set endpoints
@router.get("/assets/{asset_id}/assumptions", response_model=List[AssumptionSet])
async def list_assumption_sets(asset_id: str):
    """List assumption sets for an asset"""
    sets = assumption_set_service.list_assumption_sets(asset_id)
    return sets


@router.post("/assets/{asset_id}/assumptions", response_model=AssumptionSet)
async def create_assumption_set(
    asset_id: str,
    request: CreateAssumptionSetRequest
):
    """Create a new assumption set"""
    request.asset_id = asset_id
    assumption_set = assumption_set_service.create_assumption_set(request)
    return assumption_set


@router.put("/assumption-sets/{set_id}", response_model=AssumptionSet)
async def update_assumption_set(
    set_id: str,
    request: UpdateAssumptionSetRequest
):
    """Update an assumption set"""
    assumption_set = assumption_set_service.update_assumption_set(
        set_id=set_id,
        comparator_set=request.comparator_set,
        benefit_hypothesis=request.benefit_hypothesis,
        uptake_archetype=request.uptake_archetype,
        uptake_parameters=request.uptake_parameters
    )
    if not assumption_set:
        raise HTTPException(status_code=404, detail="Assumption set not found")
    return assumption_set


@router.post("/assumption-sets/{set_id}/lock", response_model=AssumptionSet)
async def lock_assumption_set(set_id: str):
    """Lock an assumption set"""
    assumption_set = assumption_set_service.lock_assumption_set(set_id)
    if not assumption_set:
        raise HTTPException(status_code=404, detail="Assumption set not found")
    return assumption_set


@router.post("/assumption-sets/{set_id}/unlock", response_model=AssumptionSet)
async def unlock_assumption_set(set_id: str):
    """Unlock an assumption set"""
    assumption_set = assumption_set_service.unlock_assumption_set(set_id)
    if not assumption_set:
        raise HTTPException(status_code=404, detail="Assumption set not found")
    return assumption_set


@router.post("/assumption-sets/{set_id}/clone", response_model=AssumptionSet)
async def clone_assumption_set(set_id: str, request: Dict[str, Any]):
    """Clone an assumption set"""
    new_name = request.get("new_name", f"Copy of {set_id}")
    cloned = assumption_set_service.clone_assumption_set(set_id, new_name)
    if not cloned:
        raise HTTPException(status_code=404, detail="Assumption set not found")
    return cloned

