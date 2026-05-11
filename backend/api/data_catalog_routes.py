"""
Data Catalog API Routes - Module 2: Data & Knowledge Backbone
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
import uuid
from services.data_catalog_service import data_catalog_service
from services.document_intelligence import document_intelligence_service

router = APIRouter()


@router.get("/sources")
async def list_sources(
    source_type: Optional[str] = None,
    market: Optional[str] = None
):
    """List data sources"""
    sources = data_catalog_service.list_sources(source_type=source_type, market=market)
    return {"sources": sources}


@router.post("/sources")
async def register_source(source: Dict[str, Any]):
    """Register a data source"""
    registered = data_catalog_service.register_source(
        name=source.get("name"),
        source_type=source.get("type"),
        owner=source.get("owner", "system"),
        refresh_frequency=source.get("refresh_frequency", "monthly"),
        coverage=source.get("coverage", {}),
        quality_threshold=source.get("quality_threshold", 0.9)
    )
    return registered


@router.get("/sources/{source_id}")
async def get_source(source_id: str):
    """Get source details"""
    source = data_catalog_service.get_source(source_id)
    if not source:
        # Return empty structure instead of 404
        return {
            "source_id": source_id,
            "name": None,
            "type": None,
            "status": "not_found",
            "message": "Source not found"
        }
    return source


@router.put("/sources/{source_id}")
async def update_source(source_id: str, updates: Dict[str, Any]):
    """Update source"""
    source = data_catalog_service.get_source(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    source.update(updates)
    data_catalog_service._data_sources[source_id] = source
    return source


@router.get("/quality")
async def get_quality_metrics():
    """Get data quality metrics"""
    sources = data_catalog_service.list_sources()
    
    overall_quality = sum(s.get("quality_score", 0) for s in sources) / len(sources) if sources else 0
    
    return {
        "overall_quality": overall_quality,
        "sources_by_tier": {
            "high": len([s for s in sources if s.get("quality_score", 0) >= 0.9]),
            "medium": len([s for s in sources if 0.7 <= s.get("quality_score", 0) < 0.9]),
            "low": len([s for s in sources if s.get("quality_score", 0) < 0.7])
        },
        "sources": sources
    }


@router.post("/documents/upload")
async def upload_document(
    asset_id: str,
    file_name: str,
    file_path: str,
    artifact_type: str = "protocol"
):
    """Upload and process document"""
    # In real implementation, would:
    # 1. Save file to object storage
    # 2. Extract text (OCR if needed)
    # 3. Extract entities
    # 4. Store in vector DB
    
    document_id = str(uuid.uuid4())
    
    # Placeholder extraction
    extracted = document_intelligence_service.extract_entities(document_id, "")
    
    return {
        "document_id": document_id,
        "extracted_entities": extracted,
        "status": "processed"
    }


@router.get("/documents")
async def list_documents(asset_id: Optional[str] = None):
    """List documents"""
    # Placeholder
    return {"documents": []}


@router.post("/entities/resolve")
async def resolve_entities(entities: Dict[str, List[str]]):
    """Resolve entities to canonical forms"""
    resolved = {}
    for entity_type, entity_list in entities.items():
        resolved[entity_type] = [
            {"original": e, "canonical": e, "confidence": 0.8}
            for e in entity_list
        ]
    return {"resolved": resolved}


@router.get("/lineage/{output_id}")
async def get_lineage(output_id: str):
    """Get data lineage for an output"""
    # Placeholder
    return {
        "output_id": output_id,
        "sources": [],
        "transformations": []
    }

