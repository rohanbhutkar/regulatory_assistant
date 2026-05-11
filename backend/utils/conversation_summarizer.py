"""
Summarize long conversation_history before it fills the context window.

Uses the shared LLM agent when ENABLE_CONVERSATION_SUMMARIZATION is on.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from config import settings

logger = logging.getLogger(__name__)


def _total_chars(messages: List[Dict[str, Any]]) -> int:
    return sum(len(str(m.get("content", ""))) for m in messages)


async def maybe_summarize_conversation_messages(
    messages: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    If history is long, keep head + tail and replace the middle with one summary message.

    Expects dicts with keys role, content (and optional timestamp).
    """
    if not messages or not settings.ENABLE_CONVERSATION_SUMMARIZATION:
        return messages

    max_msg = settings.CONVERSATION_SUMMARY_MAX_MESSAGES
    max_chars = settings.CONVERSATION_SUMMARY_MAX_CHARS
    if len(messages) <= max_msg and _total_chars(messages) <= max_chars:
        return messages

    head_n = settings.CONVERSATION_SUMMARY_HEAD_MESSAGES
    tail_n = settings.CONVERSATION_SUMMARY_TAIL_MESSAGES
    if len(messages) <= head_n + tail_n + 1:
        return messages

    head = messages[:head_n]
    tail = messages[-tail_n:]
    middle = messages[head_n : len(messages) - tail_n]
    transcript = "\n".join(
        f"{m.get('role', '?').upper()}: {(m.get('content') or '')[:2000]}" for m in middle
    )
    prompt = f"""Summarize the following middle segment of a clinical-research chat for downstream context.
Preserve: drug names, indications, NCT IDs, regulatory references, and user goals.
Output 6–12 bullet lines, no preamble.

TRANSCRIPT:
{transcript[:12000]}
"""
    try:
        from agents.llm_agent import llm_agent

        summary = await llm_agent.generate_response(
            prompt, system_prompt="You compress chat history for RAG-style reuse. Be factual."
        )
    except Exception as e:
        logger.warning("Conversation summarization failed: %s", e)
        return messages

    synthetic = {
        "role": "assistant",
        "content": f"[Summarized middle of conversation ({len(middle)} messages)]\n{summary.strip()}",
        "metadata": {"synthetic_summary": True, "omitted_message_count": len(middle)},
    }
    return head + [synthetic] + tail


def conversation_messages_to_dicts(conversation_history: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for m in conversation_history or []:
        if hasattr(m, "role"):
            out.append(
                {
                    "role": m.role,
                    "content": m.content,
                    "timestamp": getattr(m, "timestamp", 0),
                }
            )
        elif isinstance(m, dict):
            out.append(
                {
                    "role": m.get("role", "user"),
                    "content": m.get("content", ""),
                    "timestamp": m.get("timestamp", 0),
                }
            )
    return out
