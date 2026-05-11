"""Shared helpers for live public HTTP APIs (no site database)."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

import httpx


def truncate_text(text: str, max_chars: int) -> str:
    if not text:
        return ""
    t = text.strip()
    if len(t) <= max_chars:
        return t
    return t[: max_chars - 1].rstrip() + "…"


def safe_json_preview(obj: Any, max_chars: int = 12000) -> str:
    try:
        s = json.dumps(obj, indent=2, default=str)
    except TypeError:
        s = str(obj)
    return truncate_text(s, max_chars)


async def http_get_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Any:
    r = await client.get(url, params=params or {}, headers=headers or {})
    r.raise_for_status()
    return r.json()


async def http_post_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    json_body: Any,
    headers: Optional[Dict[str, str]] = None,
) -> Any:
    h = {"Content-Type": "application/json", **(headers or {})}
    r = await client.post(url, json=json_body, headers=h)
    r.raise_for_status()
    return r.json()


def sanitize_free_text_query(q: str, max_len: int = 400) -> str:
    if not q:
        return ""
    q = re.sub(r"\s+", " ", q).strip()
    if len(q) > max_len:
        q = q[:max_len].rsplit(" ", 1)[0]
    return q
