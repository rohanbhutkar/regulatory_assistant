"""
Token estimates for budgeting and truncation (local, no API calls).

Uses tiktoken with an encoding aligned to the active LLM when TIKTOKEN_ENCODING=auto
(OpenAI GPT-4/5-style → o200k_base; otherwise cl100k_base). Falls back to chars/3.5 when
tiktoken is missing or TOKEN_COUNT_METHOD=heuristic.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any


def _method() -> str:
    try:
        from config import settings

        return (getattr(settings, "TOKEN_COUNT_METHOD", None) or "tiktoken").lower().strip()
    except Exception:
        return "tiktoken"


def resolve_tiktoken_encoding_name() -> str:
    """
    Return a tiktoken encoding name, or 'heuristic' to skip tiktoken entirely.
    """
    try:
        from config import settings

        if _method() == "heuristic":
            return "heuristic"
        explicit = (getattr(settings, "TIKTOKEN_ENCODING", None) or "auto").strip().lower()
        if explicit and explicit != "auto":
            return explicit
        prov = getattr(settings, "LLM_PROVIDER", "anthropic")
        model = ""
        if prov == "openai":
            model = (getattr(settings, "OPENAI_MODEL", None) or "").lower()
        elif prov == "azure_openai":
            model = (settings.azure_openai_deployment or "").lower()
        else:
            model = (getattr(settings, "ANTHROPIC_MODEL", None) or "").lower()
        if prov in ("openai", "azure_openai"):
            if any(
                x in model
                for x in (
                    "gpt-5",
                    "gpt-4.1",
                    "gpt-4o",
                    "gpt-4-turbo",
                    "gpt-4-0125",
                    "gpt-4-1106",
                    "gpt-4-vision",
                    "o1",
                    "o3",
                    "o4-mini",
                )
            ):
                try:
                    import tiktoken

                    tiktoken.get_encoding("o200k_base")
                    return "o200k_base"
                except Exception:
                    return "cl100k_base"
        return "cl100k_base"
    except Exception:
        return "cl100k_base"


@lru_cache(maxsize=8)
def _encoder_for(encoding_name: str):
    if encoding_name in ("heuristic", "none", ""):
        return None
    try:
        import tiktoken

        return tiktoken.get_encoding(encoding_name)
    except Exception:
        return None


def _encoder():
    return _encoder_for(resolve_tiktoken_encoding_name())


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    enc = _encoder()
    if enc is not None:
        return len(enc.encode(str(text)))
    return int(len(str(text)) / 3.5)


def estimate_data_tokens(data: Any) -> int:
    if isinstance(data, dict):
        return sum(estimate_tokens(str(v)) for v in data.values())
    if isinstance(data, list):
        return sum(estimate_data_tokens(item) for item in data)
    return estimate_tokens(str(data))
