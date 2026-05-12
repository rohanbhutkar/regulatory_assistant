"""FastAPI dependency: one request-scoped async session with commit/rollback."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db import chat_database as chat_db

logger = logging.getLogger(__name__)


async def require_chat_db_session() -> AsyncGenerator[AsyncSession, None]:
    if not chat_db.chat_persistence_enabled() or not chat_db.chat_db_pool_ready():
        raise HTTPException(
            status_code=503,
            detail={
                "code": "chat_persistence_unavailable",
                "message": "Chat persistence is disabled or not configured.",
            },
        )
    factory = chat_db.session_factory()
    assert factory is not None
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except HTTPException:
            await session.rollback()
            raise
        except Exception as e:
            await session.rollback()
            logger.warning("chat_db_error cls=%s: %s", type(e).__name__, e)
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "chat_db_unavailable",
                    "message": "Chat storage is temporarily unavailable.",
                },
            ) from e


ChatSessionDep = Annotated[AsyncSession, Depends(require_chat_db_session)]
