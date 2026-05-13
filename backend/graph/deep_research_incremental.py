"""
Incremental deep research: after each evidence step, assess usefulness, refine a working answer,
and optionally skip remaining search nodes when marginal value is very low.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from config import settings
from agents.llm_agent import llm_agent


def truncate_for_reflection(payload: Any, max_chars: Optional[int] = None) -> str:
    """Compact JSON/text for reflection LLM."""
    limit = max_chars if max_chars is not None else int(settings.REFLECTION_PAYLOAD_MAX_CHARS)
    try:
        s = json.dumps(payload, default=str)
    except Exception:
        s = str(payload)
    if len(s) > limit:
        return s[:limit] + "\n…[truncated for reflection]"
    return s


def _parse_json_object(raw: str) -> Dict[str, Any]:
    """
    Parse the first JSON object from LLM output. Never raises; invalid JSON → {}.

    Uses JSONDecoder.raw_decode from each ``{`` so nested braces and trailing text are handled;
    avoids a second json.loads on a greedy ``{.*}`` slice raising JSONDecodeError.
    """
    s = (raw or "").strip()
    if not s:
        return {}
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, flags=re.IGNORECASE)
        s = re.sub(r"\s*```\s*$", "", s).strip()

    dec = json.JSONDecoder()

    def _try_one(candidate: str) -> Optional[Dict[str, Any]]:
        c = candidate.strip()
        if not c:
            return None
        try:
            obj = json.loads(c)
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            pass
        start = c.find("{")
        while start != -1:
            try:
                obj, _end = dec.raw_decode(c, start)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pass
            start = c.find("{", start + 1)
        return None

    parsed = _try_one(s)
    if parsed is not None:
        return parsed
    # Last resort: legacy greedy slice (still must not raise)
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if m:
        parsed = _try_one(m.group())
        if parsed is not None:
            return parsed
    return {}


async def reflect_on_step(
    query: str,
    research_spec: Dict[str, Any],
    node_id: str,
    node_type: str,
    source: Optional[str],
    result_preview: str,
    upcoming_node_descriptions: List[str],
) -> Dict[str, Any]:
    """LLM: judge this step's output and whether the pipeline should continue or skip searches."""
    brief = (research_spec.get("brief") or "")[:2000]
    upcoming_txt = "\n".join(f"- {u}" for u in upcoming_node_descriptions[:8]) or "(none listed)"
    prompt = f"""You are steering a multi-step clinical/regulatory research run. One step just finished.

USER QUERY:
{query}

RESEARCH BRIEF (contract for coverage):
{brief}

STEP JUST COMPLETED:
- node_id: {node_id}
- node_type: {node_type}
- source (if search): {source or "n/a"}

RAW / STRUCTURED OUTPUT (may be truncated only if extremely large):
{result_preview}

UPCOMING PLANNED STEPS (titles/descriptions only):
{upcoming_txt}

Return ONLY valid JSON:
{{
  "usefulness_score": 0.0,
  "source_quality": "high|medium|low|noise",
  "useful_for_answer": true,
  "rationale": "2-4 sentences: what this step contributed, reliability, gaps",
  "continue_pipeline": true,
  "skip_remaining_searches": false,
  "what_changed": "1-3 sentences: facts to fold into the running answer",
  "next_step_hint": "optional short hint for later steps, or empty string"
}}

Rules:
- usefulness_score: 0=no usable signal, 1=strong direct evidence for the user question
- Set skip_remaining_searches=true ONLY if results are empty/noise AND upcoming steps are mostly redundant searches that would not change the answer; prefer continue_pipeline=true when unsure
- Be honest if a source failed or is off-topic
"""
    raw = await llm_agent.generate_structured_response(
        prompt,
        system_prompt="You output only valid JSON for research steering.",
        max_tokens=min(1200, settings.GRAPH_PLAN_MAX_TOKENS),
    )
    if not raw.strip().startswith("{") or "Error generating" in raw:
        return {
            "usefulness_score": 0.5,
            "source_quality": "medium",
            "useful_for_answer": True,
            "rationale": "Reflection LLM unavailable or returned non-JSON; continuing pipeline.",
            "continue_pipeline": True,
            "skip_remaining_searches": False,
            "what_changed": "",
            "next_step_hint": "",
        }
    data = _parse_json_object(raw)
    # Normalize types
    try:
        data["usefulness_score"] = float(data.get("usefulness_score", 0.5))
    except (TypeError, ValueError):
        data["usefulness_score"] = 0.5
    data["useful_for_answer"] = bool(data.get("useful_for_answer", True))
    data["continue_pipeline"] = bool(data.get("continue_pipeline", True))
    data["skip_remaining_searches"] = bool(data.get("skip_remaining_searches", False))
    for k in ("rationale", "what_changed", "next_step_hint"):
        data[k] = str(data.get(k) or "").strip()
    sq = str(data.get("source_quality") or "medium").lower()
    if sq not in ("high", "medium", "low", "noise"):
        sq = "medium"
    data["source_quality"] = sq
    return data


async def refine_working_answer(
    query: str,
    research_spec: Dict[str, Any],
    previous_draft: str,
    node_id: str,
    reflection: Dict[str, Any],
    evidence_snippet: str,
) -> str:
    """Update the running narrative answer using the new step (not a dump of raw JSON)."""
    brief = (research_spec.get("brief") or "")[:1500]
    prompt = f"""You maintain a RUNNING ANSWER DRAFT for a clinical/regulatory research task.
Each turn, merge new evidence into the draft: add, correct, or refine — do not start from scratch.

USER QUERY:
{query}

BRIEF:
{brief}

PREVIOUS DRAFT (may be empty on first steps):
{previous_draft or "(no draft yet)"}

REFLECTION ON LATEST STEP ({node_id}):
- Usefulness: {reflection.get("usefulness_score")} ({reflection.get("source_quality")})
- Rationale: {reflection.get("rationale")}
- What to fold in: {reflection.get("what_changed")}

NEW EVIDENCE (may be truncated only if extremely large):
{evidence_snippet[: int(settings.REFLECTION_EVIDENCE_SNIPPET_CHARS)]}

Write the UPDATED DRAFT in Markdown:
- Lead with the best-supported claims; mark uncertainty explicitly
- Cite identifiers (NCT, PMID, URLs) when present in the evidence; **where URLs exist, use Markdown links** `[label](url)` in the prose
- If this step was low-value, say so briefly and keep prior content
- Keep length reasonable (roughly 400-2500 words); summarize if needed
"""
    draft = await llm_agent.generate_response(
        prompt,
        max_tokens=min(4096, settings.SYNTHESIS_MAX_TOKENS),
    )
    return (draft or "").strip()


def should_apply_search_skip(reflection: Dict[str, Any]) -> bool:
    """Conservative gate so we rarely abort the graph by mistake."""
    if not reflection.get("skip_remaining_searches"):
        return False
    score = float(reflection.get("usefulness_score") or 1.0)
    quality = str(reflection.get("source_quality") or "")
    if score > 0.18:
        return False
    if quality not in ("noise", "low"):
        return False
    if reflection.get("continue_pipeline", True) and reflection.get("useful_for_answer", False):
        return False
    return True


async def reflect_and_refine_step_combined(
    query: str,
    research_spec: Dict[str, Any],
    node_id: str,
    node_type: str,
    source: Optional[str],
    result_preview: str,
    upcoming_node_descriptions: List[str],
    previous_draft: str,
) -> Tuple[Dict[str, Any], str]:
    """
    Single LLM call: assess the step and produce an updated running draft (replaces reflect + refine pair).
    """
    brief = (research_spec.get("brief") or "")[:2000]
    upcoming_txt = "\n".join(f"- {u}" for u in upcoming_node_descriptions[:8]) or "(none listed)"
    ev_cap = int(settings.REFLECTION_EVIDENCE_SNIPPET_CHARS)
    prompt = f"""You steer a multi-step clinical/regulatory research run. One step just finished.

USER QUERY:
{query}

RESEARCH BRIEF:
{brief}

STEP JUST COMPLETED:
- node_id: {node_id}
- node_type: {node_type}
- source (if search): {source or "n/a"}

RAW / STRUCTURED OUTPUT (may be truncated only if extremely large):
{result_preview}

UPCOMING PLANNED STEPS:
{upcoming_txt}

PREVIOUS DRAFT (may be empty):
{previous_draft or "(no draft yet)"}

Return ONLY valid JSON with this exact structure:
{{
  "usefulness_score": 0.0,
  "source_quality": "high|medium|low|noise",
  "useful_for_answer": true,
  "rationale": "2-4 sentences",
  "continue_pipeline": true,
  "skip_remaining_searches": false,
  "what_changed": "1-3 sentences: facts to fold into the answer",
  "next_step_hint": "optional string",
  "updated_draft_markdown": "Full updated running answer in Markdown (merge new evidence; do not restart from scratch unless prior draft empty). 400-2500 words target; cite NCT/PMID when present; use Markdown links [label](url) in the text for every URL from evidence."
}}

Rules:
- usefulness_score 0=no signal, 1=strong evidence
- skip_remaining_searches=true only if results are empty/noise and further searches redundant; prefer false when unsure
- updated_draft_markdown must incorporate the reflection and evidence; if step was low-value, say so briefly and keep prior content
"""
    raw = await llm_agent.generate_structured_response(
        prompt,
        system_prompt="You output only valid JSON.",
        max_tokens=min(5000, settings.SYNTHESIS_MAX_TOKENS),
    )
    if not raw.strip().startswith("{") or "Error generating" in raw:
        fb = await reflect_on_step(
            query,
            research_spec,
            node_id,
            node_type,
            source,
            result_preview,
            upcoming_node_descriptions,
        )
        draft = await refine_working_answer(
            query,
            research_spec,
            previous_draft,
            node_id,
            fb,
            result_preview,
        )
        return fb, draft

    data = _parse_json_object(raw)
    try:
        data["usefulness_score"] = float(data.get("usefulness_score", 0.5))
    except (TypeError, ValueError):
        data["usefulness_score"] = 0.5
    data["useful_for_answer"] = bool(data.get("useful_for_answer", True))
    data["continue_pipeline"] = bool(data.get("continue_pipeline", True))
    data["skip_remaining_searches"] = bool(data.get("skip_remaining_searches", False))
    for k in ("rationale", "what_changed", "next_step_hint"):
        data[k] = str(data.get(k) or "").strip()
    sq = str(data.get("source_quality") or "medium").lower()
    if sq not in ("high", "medium", "low", "noise"):
        sq = "medium"
    data["source_quality"] = sq
    draft = str(data.pop("updated_draft_markdown", "") or "").strip()
    reflection = {k: v for k, v in data.items()}
    if not draft:
        draft = await refine_working_answer(
            query,
            research_spec,
            previous_draft,
            node_id,
            reflection,
            result_preview[:ev_cap],
        )
    return reflection, draft
