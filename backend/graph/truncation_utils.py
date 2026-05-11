"""
Token estimation and prompt truncation helpers (no heavy agent imports).

Used by DynamicReasoningEngine and unit tests.
"""
from __future__ import annotations

from typing import Any, Dict, List

from utils.token_counting import estimate_data_tokens, estimate_tokens


def calculate_dynamic_limits(data_sources: Dict[str, Any], target_max_tokens: int = 200000) -> dict:
    limits: dict = {}
    total_estimated_tokens = 0
    source_tokens: Dict[str, int] = {}
    for source_name, data in data_sources.items():
        if data:
            tokens = estimate_data_tokens(data)
            source_tokens[source_name] = tokens
            total_estimated_tokens += tokens

    print(f"🔍 Pre-truncation token estimation: {total_estimated_tokens:,} total tokens across {len(source_tokens)} sources")

    if total_estimated_tokens <= target_max_tokens:
        print(f"✅ No truncation needed - {total_estimated_tokens:,} tokens < {target_max_tokens:,} limit")
        return {source: len(data) if isinstance(data, list) else 1 for source, data in data_sources.items()}

    reduction_factor = target_max_tokens / total_estimated_tokens
    print(f"📉 Reduction factor: {reduction_factor:.2f} (need to reduce by {((1-reduction_factor)*100):.1f}%)")

    for source_name, tokens in source_tokens.items():
        data = data_sources[source_name]
        if isinstance(data, list):
            original_count = len(data)
            target_count = max(1, int(original_count * reduction_factor))
            if source_name == "trial_summaries":
                target_count = max(3, int(target_count * 1.2))
            elif source_name == "soa_table_details":
                target_count = max(2, int(target_count * 0.8))
            elif source_name == "enhanced_context":
                target_count = max(5, int(target_count * 1.5))
            target_count = min(target_count, original_count)
            limits[source_name] = target_count
            print(
                f"  📊 {source_name}: {original_count} → {target_count} items ({tokens:,} → ~{int(tokens * reduction_factor):,} tokens)"
            )
        else:
            limits[source_name] = 1

    return limits


def truncate_section_to_tokens(section: str, max_tokens: int) -> str:
    if max_tokens <= 0:
        return "[Section omitted for token budget]\n"
    est = estimate_tokens(section)
    if est <= max_tokens:
        return section
    ratio = (max_tokens / max(1, est)) * 0.92
    target_len = max(48, int(len(section) * ratio))
    truncated = section[:target_len]
    last_brace = truncated.rfind("}")
    if last_brace > target_len * 0.65:
        truncated = truncated[: last_brace + 1]
    last_period = truncated.rfind(".")
    if last_period > target_len * 0.7 and estimate_tokens(truncated) > max_tokens:
        truncated = truncated[: last_period + 1]
    if estimate_tokens(truncated) > max_tokens:
        truncated = truncated[: max(1, int(len(truncated) * 0.85))]
    return truncated + "\n\n[Section truncated to fit token limits]"


def progressive_truncation(prompt: str, target_tokens: int = 150000, sep: str = "=" * 80) -> str:
    current_tokens = estimate_tokens(prompt)
    if current_tokens <= target_tokens:
        return prompt

    print(f"🔄 Progressive truncation: {current_tokens:,} → {target_tokens:,} tokens")

    sections: List[str] = prompt.split(sep)
    budget = int(target_tokens * 0.92)

    if len(sections) < 3:
        ratio = target_tokens / max(1, current_tokens)
        target_length = int(len(prompt) * ratio * 0.88)
        truncated = prompt[:target_length]
        last_period = truncated.rfind(".")
        if last_period > int(target_length * 0.75):
            truncated = truncated[: last_period + 1]
        return truncated + "\n\n[Content aggressively truncated to fit token limits]"

    first = sections[0]
    last = sections[-1]
    middle = sections[1:-1]
    tf = estimate_tokens(first)
    tm = [estimate_tokens(s) for s in middle]
    tl = estimate_tokens(last)
    total = tf + sum(tm) + tl
    if total <= 0:
        return prompt[: max(1, len(prompt) // 2)] + "\n\n[Content aggressively truncated to fit token limits]"

    scale = min(1.0, (budget / max(1, total)) * 0.98)
    print(f"📉 Per-section scale factor: {scale:.4f}")

    out_parts: List[str] = []
    out_parts.append(truncate_section_to_tokens(first, max(120, int(tf * scale))) if first else first)
    for s, t in zip(middle, tm):
        if not s:
            out_parts.append(s)
            continue
        tok = max(80, int(t * scale))
        out_parts.append(truncate_section_to_tokens(s, tok))
    out_parts.append(truncate_section_to_tokens(last, max(200, int(tl * scale))) if last else last)

    result = sep.join(out_parts)
    print(f"📏 Progressive truncation result: {estimate_tokens(result):,} tokens")
    return result


def emergency_truncation(prompt: str, target_tokens: int = 120000) -> str:
    current_tokens = estimate_tokens(prompt)
    if current_tokens <= target_tokens:
        return prompt

    print(f"🚨 Emergency truncation: {current_tokens:,} → {target_tokens:,} tokens")

    reduction_factor = (target_tokens / current_tokens) * 0.6
    target_length = int(len(prompt) * reduction_factor)
    truncated = prompt[:target_length]
    last_brace = truncated.rfind("}")
    last_period = truncated.rfind(".")
    if last_brace > target_length * 0.8:
        truncated = truncated[: last_brace + 1]
    elif last_period > target_length * 0.8:
        truncated = truncated[: last_period + 1]

    result = truncated + "\n\n[EMERGENCY TRUNCATION: Content severely reduced to fit token limits]"
    print(f"🚨 Emergency truncation result: {estimate_tokens(result):,} tokens")
    return result
