"""
Optional LLM compression of analyze-node output for downstream synthesis.

Enable with ENABLE_NODE_OUTPUT_COMPRESSION=true and tune NODE_COMPRESSION_MIN_RAW_ITEMS.
Validated with Pydantic; one repair pass on parse failure.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from config import settings

logger = logging.getLogger(__name__)


class VerbatimQuote(BaseModel):
    source_id: str = Field(default="", description="NCT, PMID, URL, or row id")
    quote: str = Field(default="")


class CompressionBrief(BaseModel):
    claims: List[str] = Field(default_factory=list)
    verbatim_quotes: List[VerbatimQuote] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)


def _strip_json_fence(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.I)
        t = re.sub(r"\s*```\s*$", "", t)
    return t.strip()


def parse_compression_brief_llm_output(text: str) -> Optional[CompressionBrief]:
    raw = _strip_json_fence(text)
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return CompressionBrief.model_validate(data)
    except Exception as e:
        logger.debug("Compression brief JSON parse failed: %s", e)
    return None


async def repair_compression_json(raw_text: str) -> Optional[CompressionBrief]:
    """Ask LLM to emit valid JSON matching CompressionBrief."""
    from agents.llm_agent import llm_agent

    prompt = f"""The following text was supposed to be JSON for keys claims, verbatim_quotes (list of objects with source_id and quote), citations, gaps.
Return ONLY valid JSON matching that shape. Fix quotes and commas. No markdown.

BROKEN OR NON-JSON INPUT:
{raw_text[:8000]}
"""
    fixed = await llm_agent.generate_response(
        prompt, system_prompt="Output raw JSON only, no fences."
    )
    return parse_compression_brief_llm_output(fixed)


async def compress_analysis_brief_for_synthesis(
    query: str,
    analysis_report: str,
    insights: List[Any],
    raw_sample: List[Any],
) -> str:
    """Produce validated JSON text for claims, quotes, and citation ids."""
    from agents.llm_agent import llm_agent

    payload = {
        "query": query,
        "analysis_report_excerpt": (analysis_report or "")[:8000],
        "insights": (insights or [])[:40],
        "raw_sample_excerpt": (raw_sample or [])[:20],
    }
    prompt = f"""Summarize this analysis node output for a downstream synthesis model.
Return JSON only (no markdown fences) with this exact shape:
{{
  "claims": ["short factual claim", ...],
  "verbatim_quotes": [{{"source_id": "NCT01234567 or PMID or row index", "quote": "exact short quote"}}, ...],
  "citations": ["NCT...", "PMID...", "https://..."],
  "gaps": ["what was not established", ...]
}}
Use source_id from trial ids in the sample when present. Keep quotes under 400 chars each.

INPUT:
{json.dumps(payload, indent=2)[:14000]}
"""
    text = await llm_agent.generate_response(prompt)
    brief = parse_compression_brief_llm_output(text)
    if brief is not None:
        return brief.model_dump_json()
    repaired = await repair_compression_json(text)
    if repaired is not None:
        return repaired.model_dump_json()
    logger.warning("Compression brief validation failed; storing raw excerpt.")
    return json.dumps(
        {
            "claims": [],
            "verbatim_quotes": [],
            "citations": [],
            "gaps": ["compression_parse_failed"],
            "raw_fallback": text[:4000],
        }
    )


async def maybe_compress_analysis_node_output(
    query: str,
    analysis_report: str,
    analysis_results: Dict[str, Any],
) -> Optional[str]:
    if not settings.ENABLE_NODE_OUTPUT_COMPRESSION:
        return None
    raw = analysis_results.get("raw_data_sample") or []
    if len(raw) < settings.NODE_COMPRESSION_MIN_RAW_ITEMS:
        return None
    ins = analysis_results.get("insights") or []
    insights_list = ins if isinstance(ins, list) else [ins]
    try:
        return await compress_analysis_brief_for_synthesis(query, analysis_report, insights_list, raw)
    except Exception as e:
        logger.warning("Node output compression failed: %s", e)
        return None
