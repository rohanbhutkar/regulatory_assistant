"""
Map–reduce style digests of large meaningful_data blobs before final synthesis.

Each top-level key becomes a shard summarized with citation-preserving instructions.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Tuple

from config import settings
from utils.token_counting import estimate_data_tokens, estimate_tokens

logger = logging.getLogger(__name__)


async def map_reduce_meaningful_data(
    query: str,
    meaningful_data: Dict[str, Any],
) -> Tuple[str, Dict[str, Any]]:
    """
    Returns (shard_summaries_markdown, possibly_trimmed_meaningful_data).

    When disabled or under token threshold, returns ("", meaningful_data unchanged).
    """
    if not settings.MAP_REDUCE_SYNTHESIS:
        return "", meaningful_data

    total = sum(estimate_data_tokens(v) for v in meaningful_data.values() if v)
    if total < settings.MAP_REDUCE_MIN_DATA_TOKENS:
        return "", meaningful_data

    from agents.llm_agent import llm_agent

    shards: List[str] = []
    trimmed: Dict[str, Any] = dict(meaningful_data)
    max_keys = settings.MAP_REDUCE_MAX_SHARDS

    items = list(meaningful_data.items())
    items.sort(key=lambda kv: estimate_data_tokens(kv[1]), reverse=True)

    for i, (key, val) in enumerate(items[:max_keys]):
        blob = json.dumps(val, indent=2, default=str) if not isinstance(val, str) else val
        cap = settings.MAP_REDUCE_SHARD_INPUT_CHARS
        excerpt = blob[:cap]
        if len(blob) > cap:
            excerpt += f"\n... [{len(blob) - cap} chars omitted from shard input]"

        prompt = f"""Shard label: {key}
User query: {query}

Digest this JSON/data shard for a final clinical synthesis model. **Preserve jurisdictional and source distinctions** (e.g. FDA vs NMPA)—do not merge into one generic list if the data separates them.
Return markdown with:
- **Key facts** (bullets; include **agency/jurisdiction** or source domain when evident)
- **Citations**: every bullet should include NCT, PMID, URL, document title, or source id when present
- **Verbatim quotes** (short, <=240 chars) for regulatory/procedural wording when critical, with source id
- **Gaps**: what this shard does not establish

DATA:
{excerpt}
"""
        try:
            _shard_mt = getattr(
                settings, "SYNTHESIS_MAX_TOKENS", llm_agent.max_tokens
            )
            part = await llm_agent.generate_response(
                prompt,
                system_prompt="You are a precise research assistant. Never invent trial identifiers or regulations.",
                max_tokens=min(_shard_mt, 16384),
            )
            shards.append(f"### Shard: `{key}`\n{part.strip()}")
        except Exception as e:
            logger.warning("Map-reduce shard %s failed: %s", key, e)
            shards.append(f"### Shard: `{key}`\n_Summary failed; raw data retained below._")

        if settings.MAP_REDUCE_TRIM_JSON_AFTER_SUMMARY and key in trimmed:
            if estimate_tokens(blob) > settings.MAP_REDUCE_TRIM_TOKEN_THRESHOLD:
                trimmed[key] = {
                    "_map_reduce_omitted": True,
                    "_original_type": type(val).__name__,
                    "_hint": "See MAP_REDUCE_SHARD_SUMMARIES in the user message for this key.",
                }

    if not shards:
        return "", meaningful_data

    body = "\n\n".join(shards)
    return body, trimmed if settings.MAP_REDUCE_TRIM_JSON_AFTER_SUMMARY else meaningful_data
