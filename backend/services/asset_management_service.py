"""
Asset Management Service - CRUD operations for assets with validation
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from models.asset_strategy_models import (
    AssetStrategy, CreateAssetRequest, UpdateAssetRequest
)


class AssetManagementService:
    """Service for managing assets"""
    
    def __init__(self):
        # In-memory storage (can be migrated to database)
        self._assets: Dict[str, AssetStrategy] = {}
        self._initialized = False
    
    def initialize_from_trialtrove(self, loader) -> int:
        """Initialize assets - create 6 specific assets"""
        # Clear existing assets to ensure we only have the 6 specified assets
        self._assets.clear()
        
        # Create 6 specific assets as requested
        assets_data = [
            {
                "id": "asset-1",
                "asset_name": "IMMUNO-673 (Adalimumab RA Program)",
                "therapeutic_area": "Immunology",
                "indication": "Rheumatoid Arthritis",
                "moa": "TNF-alpha inhibitor",
                "development_stage": "phase_iii",
                "status": "go",
                "trial_phase": "Phase III",
                "created_by": "system",
                "last_updated": datetime.now().isoformat()
            },
            {
                "id": "asset-2",
                "asset_name": "ONCO-892 (CAR-T Cell Therapy Program)",
                "therapeutic_area": "Oncology",
                "indication": "B-Cell Acute Lymphoblastic Leukemia",
                "moa": "CAR-T cell therapy",
                "development_stage": "phase_ii",
                "status": "go",
                "trial_phase": "Phase II",
                "created_by": "system",
                "last_updated": datetime.now().isoformat()
            },
            {
                "id": "asset-3",
                "asset_name": "BIO-2847 (Pembrolizumab NSCLC Program)",
                "therapeutic_area": "Oncology",
                "indication": "Non-Small Cell Lung Cancer",
                "moa": "PD-1 inhibitor",
                "development_stage": "phase_iii",
                "status": "go",
                "trial_phase": "Phase III",
                "created_by": "system",
                "last_updated": datetime.now().isoformat()
            },
            {
                "id": "asset-4",
                "asset_name": "RARE-451 (Eculizumab PNH Program)",
                "therapeutic_area": "Hematology",
                "indication": "Paroxysmal Nocturnal Hemoglobinuria",
                "moa": "C5 complement inhibitor",
                "development_stage": "phase_iii",
                "status": "go",
                "trial_phase": "Phase III",
                "created_by": "system",
                "last_updated": datetime.now().isoformat()
            },
            {
                "id": "asset-5",
                "asset_name": "METAB-789 (Semaglutide GLP-1 Program)",
                "therapeutic_area": "Metabolism",
                "indication": "Type 2 Diabetes and Obesity",
                "moa": "GLP-1 receptor agonist",
                "development_stage": "phase_iii",
                "status": "go",
                "trial_phase": "Phase III",
                "created_by": "system",
                "last_updated": datetime.now().isoformat()
            },
            {
                "id": "asset-6",
                "asset_name": "GENE-234 (Adeno-associated Virus Gene Therapy)",
                "therapeutic_area": "Rare Disease",
                "indication": "Spinal Muscular Atrophy",
                "moa": "AAV gene therapy",
                "development_stage": "phase_ii",
                "status": "go",
                "trial_phase": "Phase II",
                "created_by": "system",
                "last_updated": datetime.now().isoformat()
            }
        ]
        
        for asset_data in assets_data:
            try:
                asset = AssetStrategy(**asset_data)
                self._assets[asset_data["id"]] = asset
            except Exception as e:
                print(f"Error creating asset {asset_data.get('id')}: {e}")
        
        self._initialized = True
        return len(self._assets)
    
    def _map_phase_to_stage(self, phase: str) -> Optional[str]:
        """Map trial phase to development stage"""
        phase_lower = phase.lower() if phase else ""
        if 'phase i' in phase_lower or 'phase 1' in phase_lower:
            return 'phase_i'
        elif 'phase ii' in phase_lower or 'phase 2' in phase_lower:
            return 'phase_ii'
        elif 'phase iii' in phase_lower or 'phase 3' in phase_lower:
            return 'phase_iii'
        elif 'preclinical' in phase_lower:
            return 'preclinical'
        elif 'discovery' in phase_lower:
            return 'discovery'
        return None
    
    def create_asset(self, request: CreateAssetRequest, created_by: str = "system") -> AssetStrategy:
        """Create a new asset"""
        asset_id = f"asset_{str(uuid.uuid4())[:8]}"
        
        asset = AssetStrategy(
            id=asset_id,
            asset_name=request.asset_name,
            therapeutic_area=request.therapeutic_area,
            indication=request.indication,
            moa=request.moa,
            roa=request.roa,
            development_stage=request.development_stage,
            status=request.status,
            created_by=created_by,
            last_updated=datetime.now().isoformat()
        )
        
        self._assets[asset_id] = asset
        return asset
    
    def get_asset(self, asset_id: str) -> Optional[AssetStrategy]:
        """Get asset by ID"""
        return self._assets.get(asset_id)
    
    def update_asset(self, asset_id: str, request: UpdateAssetRequest) -> Optional[AssetStrategy]:
        """Update an existing asset"""
        asset = self._assets.get(asset_id)
        if not asset:
            return None
        
        # Update fields if provided
        update_data = request.dict(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(asset, key):
                setattr(asset, key, value)
        
        asset.last_updated = datetime.now().isoformat()
        self._assets[asset_id] = asset
        return asset
    
    def delete_asset(self, asset_id: str) -> bool:
        """Soft delete an asset (mark as deleted, don't actually remove)"""
        asset = self._assets.get(asset_id)
        if not asset:
            return False
        
        # In a real implementation, we'd mark as deleted
        # For now, we'll actually remove it
        del self._assets[asset_id]
        return True
    
    def list_assets(
        self,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "asset_name",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 50
    ) -> tuple[List[AssetStrategy], int]:
        """List assets with filtering, sorting, and pagination"""
        assets = list(self._assets.values())
        
        # Filter out devices - exclude assets with device-related keywords in name
        device_keywords = ['device', 'implant', 'prosthesis', 'stent', 'catheter', 'pacemaker', 
                          'defibrillator', 'sensor', 'monitor', 'scanner', 'system', 'apparatus']
        assets = [a for a in assets if not any(
            keyword in a.asset_name.lower() for keyword in device_keywords
        )]
        
        # Apply filters
        if filters:
            if filters.get("therapeutic_area"):
                assets = [a for a in assets if a.therapeutic_area in filters["therapeutic_area"]]
            if filters.get("development_stage"):
                assets = [a for a in assets if a.development_stage in filters["development_stage"]]
            if filters.get("status"):
                assets = [a for a in assets if a.status in filters["status"]]
            if filters.get("indication"):
                assets = [a for a in assets if a.indication and a.indication in filters["indication"]]
        
        # Apply sorting
        reverse = sort_order == "desc"
        if sort_by == "asset_name":
            assets.sort(key=lambda x: x.asset_name, reverse=reverse)
        elif sort_by == "development_stage":
            assets.sort(key=lambda x: x.development_stage or "", reverse=reverse)
        elif sort_by == "last_updated":
            assets.sort(key=lambda x: x.last_updated, reverse=reverse)
        
        # Apply pagination
        total_count = len(assets)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_assets = assets[start_idx:end_idx]
        
        return paginated_assets, total_count
    
    def search_assets(self, query: str) -> List[AssetStrategy]:
        """Search assets by name, indication, or therapeutic area"""
        query_lower = query.lower()
        results = []
        
        for asset in self._assets.values():
            if (query_lower in asset.asset_name.lower() or
                (asset.indication and query_lower in asset.indication.lower()) or
                query_lower in asset.therapeutic_area.lower()):
                results.append(asset)
        
        return results
    
    def bulk_import(self, assets: List[Dict[str, Any]]) -> List[AssetStrategy]:
        """Bulk import assets"""
        imported = []
        for asset_data in assets:
            try:
                asset = AssetStrategy(**asset_data)
                if not asset.id:
                    asset.id = f"asset_{str(uuid.uuid4())[:8]}"
                self._assets[asset.id] = asset
                imported.append(asset)
            except Exception as e:
                print(f"Error importing asset: {e}")
                continue
        return imported
    
    def bulk_export(self, asset_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Export assets to dict format"""
        if asset_ids:
            assets = [self._assets[aid] for aid in asset_ids if aid in self._assets]
        else:
            assets = list(self._assets.values())
        
        return [asset.dict() for asset in assets]
    
    def get_asset_relationships(self, asset_id: str) -> Dict[str, Any]:
        """Get related assets (parent/child, related)"""
        # Placeholder for relationship management
        return {
            "parent_assets": [],
            "child_assets": [],
            "related_assets": []
        }


# Global instance
asset_management_service = AssetManagementService()

