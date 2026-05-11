"""Regulatory Intelligence: document upload and text extraction."""
from __future__ import annotations

import io
from fastapi import APIRouter, File, HTTPException, UploadFile

from services.regulatory_document_store import regulatory_document_store

router = APIRouter()

MAX_RESPONSE_EXCERPT = 24_000


def _extract_pdf(raw: bytes) -> str:
    import fitz  # PyMuPDF

    text_parts: list[str] = []
    with fitz.open(stream=raw, filetype="pdf") as doc:
        for page in doc:
            text_parts.append(page.get_text() or "")
    return "\n".join(text_parts).strip()


def _extract_docx(raw: bytes) -> str:
    from docx import Document

    file_obj = io.BytesIO(raw)
    document = Document(file_obj)
    return "\n".join(p.text for p in document.paragraphs if p.text).strip()


def _extract_text_file(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace").strip()


@router.post("/documents")
async def upload_regulatory_document(
    file: UploadFile = File(...),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    lower = file.filename.lower()
    try:
        if lower.endswith(".pdf"):
            text = _extract_pdf(raw)
        elif lower.endswith(".docx"):
            text = _extract_docx(raw)
        elif lower.endswith(".txt") or lower.endswith(".csv"):
            text = _extract_text_file(raw)
        elif lower.endswith(".doc"):
            raise HTTPException(
                status_code=400,
                detail="Legacy .doc is not supported; please save as .docx or PDF.",
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported type. Use PDF, DOCX, TXT, or CSV.",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not read document: {e!s}") from e

    meta = regulatory_document_store.save(file.filename, text)
    excerpt = text[:MAX_RESPONSE_EXCERPT]
    excerpt_truncated = len(text) > MAX_RESPONSE_EXCERPT

    return {
        **meta,
        "excerpt": excerpt,
        "excerpt_truncated": excerpt_truncated,
        "mime_type": file.content_type,
    }
