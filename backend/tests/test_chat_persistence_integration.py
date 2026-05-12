"""Integration test: chat API against Postgres (docker-compose postgres:5432)."""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette import status

pytest.importorskip("asyncpg")

pytestmark = [pytest.mark.asyncio, pytest.mark.chat_integration]


def _pg_url() -> str | None:
    return (os.getenv("DATABASE_URL") or os.getenv("REGULATORY_DATABASE_URL") or "").strip() or None


@pytest.fixture
async def chat_client():
    url = _pg_url()
    if not url:
        pytest.skip("Set DATABASE_URL (e.g. postgresql+asyncpg://regulatory:regulatory@127.0.0.1:5432/regulatory_chat)")
    os.environ["DATABASE_URL"] = url
    os.environ["CHAT_PERSISTENCE_ENABLED"] = "true"
    os.environ["CHAT_AUTO_CREATE_SCHEMA"] = "true"

    from fastapi import FastAPI

    from api.chat_persistence_routes import router as chat_router
    from api.chat_rate_limit import limiter
    from db.chat_database import dispose_chat_database, init_chat_database

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await init_chat_database()
        yield
        await dispose_chat_database()

    app = FastAPI(lifespan=lifespan)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.include_router(chat_router, prefix="/api/chat")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_chat_bootstrap_session_message_complete_turn(chat_client: AsyncClient):
    r = await chat_client.post("/api/chat/visitors/bootstrap")
    assert r.status_code == status.HTTP_200_OK
    assert r.json().get("visitor_id")

    r2 = await chat_client.post(
        "/api/chat/sessions",
        json={"title": "pytest session", "variant": "regulatory"},
    )
    assert r2.status_code == status.HTTP_200_OK
    sid = r2.json()["id"]

    uid = str(uuid.uuid4())
    r3 = await chat_client.post(
        f"/api/chat/sessions/{sid}/messages",
        json={"content": "hello from test", "metadata": {}, "client_message_id": uid},
    )
    assert r3.status_code == status.HTTP_200_OK

    idem = f"asst-{uid}"
    r4 = await chat_client.post(
        f"/api/chat/sessions/{sid}/complete-turn",
        json={"content": "assistant reply", "metadata": {"k": 1}, "idempotency_key": idem},
        headers={"Idempotency-Key": idem},
    )
    assert r4.status_code == status.HTTP_200_OK
    assert r4.json()["message"]["role"] == "assistant"

    r5 = await chat_client.post(
        f"/api/chat/sessions/{sid}/complete-turn",
        json={"content": "assistant reply", "metadata": {"k": 1}, "idempotency_key": idem},
        headers={"Idempotency-Key": idem},
    )
    assert r5.status_code == status.HTTP_200_OK
    assert r5.json().get("duplicate") is True

    r6 = await chat_client.get(f"/api/chat/sessions/{sid}/messages")
    assert r6.status_code == status.HTTP_200_OK
    msgs = r6.json()["messages"]
    assert len(msgs) >= 2
