"""
Decision Cut Service - Immutable snapshots of asset state
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import json
try:
    from deepdiff import DeepDiff
except ImportError:
    # Fallback if deepdiff not available
    def DeepDiff(a, b, **kwargs):
        # Simple diff implementation
        changes = {}
        if isinstance(a, dict) and isinstance(b, dict):
            for key in set(a.keys()) | set(b.keys()):
                if key not in a:
                    changes[f"added.{key}"] = b[key]
                elif key not in b:
                    changes[f"removed.{key}"] = a[key]
                elif a[key] != b[key]:
                    changes[f"changed.{key}"] = {"old": a[key], "new": b[key]}
        return type('obj', (object,), {'values_changed': changes, 'dictionary_item_added': [], 'dictionary_item_removed': []})()
from models.asset_strategy_models import (
    DecisionCut, DecisionCutDiff, CreateDecisionCutRequest
)
from services.asset_management_service import asset_management_service


class DecisionCutService:
    """Service for managing decision cuts (immutable snapshots)"""
    
    def __init__(self):
        # In-memory storage
        self._decision_cuts: Dict[str, DecisionCut] = {}
        self._asset_cuts: Dict[str, List[str]] = {}  # asset_id -> list of cut IDs
    
    def create_decision_cut(
        self,
        request: CreateDecisionCutRequest,
        frozen_by: str
    ) -> DecisionCut:
        """Create an immutable snapshot of asset state"""
        # Get current asset state
        asset = asset_management_service.get_asset(request.asset_id)
        if not asset:
            raise ValueError(f"Asset {request.asset_id} not found")
        
        # Serialize entire asset state
        snapshot_data = asset.dict()
        
        # Get previous cut if exists
        previous_cut_id = None
        asset_cuts = self._asset_cuts.get(request.asset_id, [])
        if asset_cuts:
            # Get the latest cut
            latest_cut = self._decision_cuts[asset_cuts[-1]]
            previous_cut_id = latest_cut.id
        
        # Create decision cut
        decision_cut = DecisionCut(
            id=str(uuid.uuid4()),
            asset_id=request.asset_id,
            cut_name=request.cut_name,
            cut_description=request.cut_description,
            frozen_at=datetime.now().isoformat(),
            frozen_by=frozen_by,
            snapshot_data=snapshot_data,
            previous_cut_id=previous_cut_id,
            status="draft"
        )
        
        # Store
        self._decision_cuts[decision_cut.id] = decision_cut
        
        # Track by asset
        if request.asset_id not in self._asset_cuts:
            self._asset_cuts[request.asset_id] = []
        self._asset_cuts[request.asset_id].append(decision_cut.id)
        
        return decision_cut
    
    def get_decision_cut(self, cut_id: str) -> Optional[DecisionCut]:
        """Get decision cut by ID"""
        return self._decision_cuts.get(cut_id)
    
    def list_decision_cuts(self, asset_id: str) -> List[DecisionCut]:
        """List all decision cuts for an asset (chronological)"""
        cut_ids = self._asset_cuts.get(asset_id, [])
        cuts = [self._decision_cuts[cid] for cid in cut_ids if cid in self._decision_cuts]
        # Sort by frozen_at
        cuts.sort(key=lambda x: x.frozen_at)
        return cuts
    
    def get_latest_approved_cut(self, asset_id: str) -> Optional[DecisionCut]:
        """Get the latest approved decision cut for an asset"""
        cuts = self.list_decision_cuts(asset_id)
        approved_cuts = [c for c in cuts if c.status == "approved"]
        if approved_cuts:
            return approved_cuts[-1]  # Latest approved
        return None
    
    def compare_decision_cuts(self, cut1_id: str, cut2_id: str) -> DecisionCutDiff:
        """Compare two decision cuts and return differences"""
        cut1 = self._decision_cuts.get(cut1_id)
        cut2 = self._decision_cuts.get(cut2_id)
        
        if not cut1 or not cut2:
            raise ValueError("One or both decision cuts not found")
        
        # Use DeepDiff to find differences
        diff = DeepDiff(cut1.snapshot_data, cut2.snapshot_data, ignore_order=True)
        
        # Extract changes
        changes = {}
        added_items = []
        removed_items = []
        modified_items = []
        
        if 'dictionary_item_added' in diff:
            for item in diff['dictionary_item_added']:
                added_items.append(str(item))
        
        if 'dictionary_item_removed' in diff:
            for item in diff['dictionary_item_removed']:
                removed_items.append(str(item))
        
        if 'values_changed' in diff:
            for key, change in diff['values_changed'].items():
                modified_items.append(str(key))
                changes[str(key)] = {
                    "old_value": change.get("old_value"),
                    "new_value": change.get("new_value")
                }
        
        # Calculate impact assessment
        impact_assessment = self._calculate_impact(changes, added_items, removed_items)
        
        return DecisionCutDiff(
            cut1_id=cut1_id,
            cut2_id=cut2_id,
            changes=changes,
            added_items=added_items,
            removed_items=removed_items,
            modified_items=modified_items,
            impact_assessment=impact_assessment
        )
    
    def _calculate_impact(
        self,
        changes: Dict[str, Any],
        added_items: List[str],
        removed_items: List[str]
    ) -> Dict[str, Any]:
        """Calculate which downstream calculations need re-run"""
        impact = {
            "needs_recalculation": [],
            "affected_modules": []
        }
        
        # Check what fields changed
        changed_fields = set(changes.keys()) | set(added_items) | set(removed_items)
        
        # Map fields to modules
        field_to_module = {
            "moa": ["pricing", "hta"],
            "indication": ["pricing", "hta", "financial"],
            "subpopulations": ["pricing", "financial"],
            "comparator_set": ["pricing", "hta"],
            "benefit_hypothesis": ["hta"],
            "uptake_archetype": ["financial"],
            "launch_sequence": ["financial"],
            "expected_launch_dates": ["financial"]
        }
        
        affected_modules = set()
        for field in changed_fields:
            for module in field_to_module.get(field, []):
                affected_modules.add(module)
        
        impact["affected_modules"] = list(affected_modules)
        
        if "pricing" in affected_modules:
            impact["needs_recalculation"].append("price_potential")
        if "hta" in affected_modules:
            impact["needs_recalculation"].append("hta_assessment")
        if "financial" in affected_modules:
            impact["needs_recalculation"].append("financial_projection")
        
        return impact
    
    def update_decision_cut_status(self, cut_id: str, status: str) -> Optional[DecisionCut]:
        """Update decision cut status"""
        cut = self._decision_cuts.get(cut_id)
        if not cut:
            return None
        
        cut.status = status
        self._decision_cuts[cut_id] = cut
        return cut


# Global instance
decision_cut_service = DecisionCutService()

