"""
USDM ID Generator
Generates unique IDs for USDM entities following pattern: EntityType_Number
"""

class IDGenerator:
    """
    Generates unique IDs for USDM entities.
    IDs follow pattern: EntityType_Number (e.g., 'StudyArm_1', 'StudyArm_2')
    """
    
    def __init__(self):
        self.counters = {}
        self.registry = set()
    
    def generate(self, entity_type: str) -> str:
        """
        Generate a unique ID for the given entity type.
        
        Args:
            entity_type: USDM entity class name (e.g., 'StudyArm', 'StudyEpoch')
        
        Returns:
            Unique ID string (e.g., 'StudyArm_1', 'StudyArm_2')
        
        Example:
            >>> id_gen = IDGenerator()
            >>> id_gen.generate('StudyArm')
            'StudyArm_1'
            >>> id_gen.generate('StudyArm')
            'StudyArm_2'
        """
        if entity_type not in self.counters:
            self.counters[entity_type] = 0
        
        self.counters[entity_type] += 1
        id_str = f"{entity_type}_{self.counters[entity_type]}"
        
        self.registry.add(id_str)
        return id_str
    
    def reset(self):
        """Reset all counters (useful for testing)"""
        self.counters = {}
        self.registry = set()
    
    def get_all_ids(self) -> set:
        """Get all generated IDs"""
        return self.registry.copy()








