"""
Offline / pytest hooks: LLM-as-judge for deep-research completeness (optional, uses live LLM when run).
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from agents.llm_agent import llm_agent


async def llm_judge_completeness(
    user_query: str,
    outline: List[Dict[str, Any]],
    answer_text: str,
    citations_json: str = "[]",
) -> Dict[str, Any]:
    """
    Returns JSON: score 1-5, passes bool, rationale str.
    Use from tests with @pytest.mark.asyncio when API keys are available.
    """
    prompt = f"""Rate how well the answer covers the planned outline for the user query.

USER QUERY:
{user_query}

OUTLINE (section_id + title):
{json.dumps(outline, indent=2)[:8000]}

ANSWER:
{answer_text[:12000]}

CITATIONS (truncated):
{citations_json[:4000]}

Return ONLY JSON:
{{ "score": 1-5, "passes": true/false, "rationale": "short" }}
"""
    raw = await llm_agent.generate_structured_response(
        prompt,
        system_prompt="You output only valid JSON.",
        max_tokens=512,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return {"score": 0, "passes": False, "rationale": "parse_error"}
        return json.loads(m.group())
