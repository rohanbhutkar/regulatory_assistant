"""
Evidence Artifact Service - Document storage and entity extraction
Enhanced with graph backend agents for intelligent entity extraction
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
import logging
from models.asset_strategy_models import EvidenceArtifact, EvidenceArtifactType

logger = logging.getLogger(__name__)


class EvidenceArtifactService:
    """Service for managing evidence artifacts"""
    
    def __init__(self):
        # In-memory storage
        self._artifacts: Dict[str, EvidenceArtifact] = {}
        self._asset_artifacts: Dict[str, List[str]] = {}  # asset_id -> list of artifact IDs
    
    def upload_artifact(
        self,
        asset_id: str,
        artifact_type: EvidenceArtifactType,
        file_name: str,
        file_path: str,
        file_size: Optional[int] = None,
        uploaded_by: str = "system",
        extracted_entities: Optional[Dict[str, Any]] = None
    ) -> EvidenceArtifact:
        """Upload and store an evidence artifact with optional entity extraction"""
        artifact = EvidenceArtifact(
            id=str(uuid.uuid4()),
            asset_id=asset_id,
            artifact_type=artifact_type,
            file_name=file_name,
            file_path=file_path,
            file_size=file_size,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.now().isoformat(),
            extracted_entities=extracted_entities or {}
        )
        
        self._artifacts[artifact.id] = artifact
        
        # Track by asset
        if asset_id not in self._asset_artifacts:
            self._asset_artifacts[asset_id] = []
        self._asset_artifacts[asset_id].append(artifact.id)
        
        return artifact
    
    async def extract_entities_intelligent(
        self,
        artifact_id: str,
        content: str,
        asset_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Intelligently extract entities from evidence artifact using graph backend agents
        
        Uses FDA Labels, PubMed, TrialTrove agents to extract and validate entities
        """
        try:
            from graph.dynamic_reasoning_engine import DynamicReasoningEngine
            from agents.fda_labels_agent import fda_labels_agent
            from agents.pubmed_agent import pubmed_agent
            from agents.trialtrove_agent import trialtrove_agent
            
            extracted_entities = {
                "drugs": [],
                "indications": [],
                "endpoints": [],
                "comparators": [],
                "sources": []
            }
            
            # Extract drug names using FDA Labels agent
            if asset_context and asset_context.get("asset_name"):
                drug_name = asset_context["asset_name"].split('(')[0].strip()
                try:
                    fda_results = await fda_labels_agent.search_labels(drug_name, max_results=5)
                    if fda_results:
                        extracted_entities["drugs"].extend([
                            {"name": r.get("drug_name", ""), "source": "fda_labels", "confidence": 0.9}
                            for r in fda_results if r.get("drug_name")
                        ])
                        extracted_entities["sources"].append("fda_labels")
                except Exception as e:
                    logger.warning(f"Error extracting drugs from FDA Labels: {e}")
            
            # Extract indications from content
            if asset_context and asset_context.get("indication"):
                extracted_entities["indications"].append({
                    "name": asset_context["indication"],
                    "source": "asset_context",
                    "confidence": 1.0
                })
            
            # Search for related trials using TrialTrove
            if asset_context:
                indication = asset_context.get("indication") or asset_context.get("therapeutic_area", "")
                if indication:
                    try:
                        trial_results = await trialtrove_agent.search_studies(indication, max_results=5)
                        if trial_results:
                            extracted_entities["comparators"].extend([
                                {"name": r.title or "", "source": "trialtrove", "confidence": 0.8}
                                for r in trial_results if r.title
                            ])
                            extracted_entities["sources"].append("trialtrove")
                    except Exception as e:
                        logger.warning(f"Error extracting comparators from TrialTrove: {e}")
            
            # Update artifact with extracted entities
            self.update_extracted_entities(artifact_id, extracted_entities, confidence_score=0.85)
            
            return extracted_entities
            
        except Exception as e:
            logger.error(f"Error in intelligent entity extraction: {e}")
            return {"error": str(e)}
    
    def get_artifact(self, artifact_id: str) -> Optional[EvidenceArtifact]:
        """Get artifact by ID"""
        return self._artifacts.get(artifact_id)
    
    def list_artifacts(
        self,
        asset_id: Optional[str] = None,
        artifact_type: Optional[EvidenceArtifactType] = None
    ) -> List[EvidenceArtifact]:
        """List artifacts with optional filtering"""
        if asset_id:
            artifact_ids = self._asset_artifacts.get(asset_id, [])
            artifacts = [self._artifacts[aid] for aid in artifact_ids if aid in self._artifacts]
        else:
            artifacts = list(self._artifacts.values())
        
        # Filter by type if specified
        if artifact_type:
            artifacts = [a for a in artifacts if a.artifact_type == artifact_type]
        
        # Sort by upload date (newest first)
        artifacts.sort(key=lambda x: x.uploaded_at, reverse=True)
        
        return artifacts
    
    def update_extracted_entities(
        self,
        artifact_id: str,
        extracted_entities: Dict[str, Any],
        confidence_score: Optional[float] = None
    ) -> Optional[EvidenceArtifact]:
        """Update extracted entities from document intelligence"""
        artifact = self._artifacts.get(artifact_id)
        if not artifact:
            return None
        
        artifact.extracted_entities = extracted_entities
        if confidence_score is not None:
            artifact.confidence_score = confidence_score
        
        self._artifacts[artifact_id] = artifact
        return artifact
    
    def link_to_asset_fields(
        self,
        artifact_id: str,
        linked_fields: Dict[str, Any]
    ) -> Optional[EvidenceArtifact]:
        """Link artifact to specific asset fields"""
        artifact = self._artifacts.get(artifact_id)
        if not artifact:
            return None
        
        artifact.linked_fields = linked_fields
        self._artifacts[artifact_id] = artifact
        return artifact
    
    def delete_artifact(self, artifact_id: str) -> bool:
        """Delete an artifact"""
        artifact = self._artifacts.get(artifact_id)
        if not artifact:
            return False
        
        # Remove from asset tracking
        asset_id = artifact.asset_id
        if asset_id in self._asset_artifacts:
            self._asset_artifacts[asset_id] = [
                aid for aid in self._asset_artifacts[asset_id] if aid != artifact_id
            ]
        
        del self._artifacts[artifact_id]
        return True


# Global instance
evidence_artifact_service = EvidenceArtifactService()

