"""In-memory store for regulatory document text extracted on upload (per-process)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import uuid


class RegulatoryDocumentStore:
    def __init__(self) -> None:
        self._documents: Dict[str, Dict[str, Any]] = {}

    def save(self, filename: str, text: str, max_chars: int = 2_000_000) -> Dict[str, Any]:
        doc_id = str(uuid.uuid4())
        truncated = len(text) > max_chars
        stored = text[:max_chars] if truncated else text
        self._documents[doc_id] = {
            "filename": filename,
            "text": stored,
            "truncated": truncated,
            "original_length": len(text),
        }
        return {
            "document_id": doc_id,
            "filename": filename,
            "char_count": len(stored),
            "truncated": truncated,
            "original_length": len(text),
        }

    def get(self, document_id: str) -> Optional[Dict[str, Any]]:
        return self._documents.get(document_id)

    def get_many(self, document_ids: List[str]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for doc_id in document_ids:
            rec = self._documents.get(doc_id)
            if rec:
                out.append(
                    {
                        "id": doc_id,
                        "filename": rec["filename"],
                        "extracted_text": rec["text"],
                        "truncated_storage": rec["truncated"],
                    }
                )
        return out


regulatory_document_store = RegulatoryDocumentStore()
