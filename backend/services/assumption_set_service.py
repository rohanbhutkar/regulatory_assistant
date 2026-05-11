"""
Assumption Set Service - CRUD for assumption sets
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from models.asset_strategy_models import AssumptionSet, Comparator, CreateAssumptionSetRequest


class AssumptionSetService:
    """Service for managing assumption sets"""
    
    def __init__(self):
        # In-memory storage
        self._assumption_sets: Dict[str, AssumptionSet] = {}
        self._asset_assumption_sets: Dict[str, List[str]] = {}  # asset_id -> list of set IDs
    
    def create_assumption_set(
        self,
        request: CreateAssumptionSetRequest
    ) -> AssumptionSet:
        """Create a new assumption set"""
        assumption_set = AssumptionSet(
            id=str(uuid.uuid4()),
            asset_id=request.asset_id,
            name=request.name,
            comparator_set=request.comparator_set or [],
            benefit_hypothesis=request.benefit_hypothesis,
            uptake_archetype=request.uptake_archetype,
            uptake_parameters=request.uptake_parameters or {}
        )
        
        self._assumption_sets[assumption_set.id] = assumption_set
        
        # Track by asset
        if request.asset_id not in self._asset_assumption_sets:
            self._asset_assumption_sets[request.asset_id] = []
        self._asset_assumption_sets[request.asset_id].append(assumption_set.id)
        
        return assumption_set
    
    def get_assumption_set(self, set_id: str) -> Optional[AssumptionSet]:
        """Get assumption set by ID"""
        return self._assumption_sets.get(set_id)
    
    def list_assumption_sets(self, asset_id: str) -> List[AssumptionSet]:
        """List all assumption sets for an asset"""
        set_ids = self._asset_assumption_sets.get(asset_id, [])
        sets = [self._assumption_sets[sid] for sid in set_ids if sid in self._assumption_sets]
        # Sort by updated_at (newest first)
        sets.sort(key=lambda x: x.updated_at, reverse=True)
        return sets
    
    def update_assumption_set(
        self,
        set_id: str,
        comparator_set: Optional[List[Comparator]] = None,
        benefit_hypothesis: Optional[str] = None,
        uptake_archetype: Optional[str] = None,
        uptake_parameters: Optional[Dict[str, Any]] = None
    ) -> Optional[AssumptionSet]:
        """Update an assumption set"""
        assumption_set = self._assumption_sets.get(set_id)
        if not assumption_set:
            return None
        
        # Check if locked
        if assumption_set.is_locked:
            raise ValueError("Assumption set is locked and cannot be modified")
        
        # Update fields
        if comparator_set is not None:
            assumption_set.comparator_set = comparator_set
        if benefit_hypothesis is not None:
            assumption_set.benefit_hypothesis = benefit_hypothesis
        if uptake_archetype is not None:
            assumption_set.uptake_archetype = uptake_archetype
        if uptake_parameters is not None:
            assumption_set.uptake_parameters = uptake_parameters
        
        assumption_set.updated_at = datetime.now().isoformat()
        assumption_set.version += 1
        
        self._assumption_sets[set_id] = assumption_set
        return assumption_set
    
    def lock_assumption_set(self, set_id: str) -> Optional[AssumptionSet]:
        """Lock an assumption set to prevent edits"""
        assumption_set = self._assumption_sets.get(set_id)
        if not assumption_set:
            return None
        
        assumption_set.is_locked = True
        self._assumption_sets[set_id] = assumption_set
        return assumption_set
    
    def unlock_assumption_set(self, set_id: str) -> Optional[AssumptionSet]:
        """Unlock an assumption set"""
        assumption_set = self._assumption_sets.get(set_id)
        if not assumption_set:
            return None
        
        assumption_set.is_locked = False
        self._assumption_sets[set_id] = assumption_set
        return assumption_set
    
    def clone_assumption_set(self, set_id: str, new_name: str) -> Optional[AssumptionSet]:
        """Clone an assumption set"""
        original = self._assumption_sets.get(set_id)
        if not original:
            return None
        
        cloned = AssumptionSet(
            id=str(uuid.uuid4()),
            asset_id=original.asset_id,
            name=new_name,
            comparator_set=original.comparator_set.copy() if original.comparator_set else [],
            benefit_hypothesis=original.benefit_hypothesis,
            uptake_archetype=original.uptake_archetype,
            uptake_parameters=original.uptake_parameters.copy() if original.uptake_parameters else {},
            is_locked=False,
            version=1
        )
        
        self._assumption_sets[cloned.id] = cloned
        
        # Track by asset
        if original.asset_id not in self._asset_assumption_sets:
            self._asset_assumption_sets[original.asset_id] = []
        self._asset_assumption_sets[original.asset_id].append(cloned.id)
        
        return cloned
    
    def add_comparator(self, set_id: str, comparator: Comparator) -> Optional[AssumptionSet]:
        """Add a comparator to an assumption set"""
        assumption_set = self._assumption_sets.get(set_id)
        if not assumption_set:
            return None
        
        if assumption_set.is_locked:
            raise ValueError("Assumption set is locked")
        
        assumption_set.comparator_set.append(comparator)
        assumption_set.updated_at = datetime.now().isoformat()
        assumption_set.version += 1
        
        self._assumption_sets[set_id] = assumption_set
        return assumption_set
    
    def remove_comparator(self, set_id: str, comparator_drug: str) -> Optional[AssumptionSet]:
        """Remove a comparator from an assumption set"""
        assumption_set = self._assumption_sets.get(set_id)
        if not assumption_set:
            return None
        
        if assumption_set.is_locked:
            raise ValueError("Assumption set is locked")
        
        assumption_set.comparator_set = [
            c for c in assumption_set.comparator_set if c.drug != comparator_drug
        ]
        assumption_set.updated_at = datetime.now().isoformat()
        assumption_set.version += 1
        
        self._assumption_sets[set_id] = assumption_set
        return assumption_set


# Global instance
assumption_set_service = AssumptionSetService()


