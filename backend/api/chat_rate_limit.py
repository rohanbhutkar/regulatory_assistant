"""Shared SlowAPI limiter for chat routes."""

from slowapi import Limiter
from starlette.requests import Request


def _rate_key(request: Request) -> str:
    xf = request.headers.get("x-forwarded-for")
    if xf:
        return xf.split(",")[0].strip()
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


limiter = Limiter(key_func=_rate_key)
