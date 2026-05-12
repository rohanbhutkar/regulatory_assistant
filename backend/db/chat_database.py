"""Async engine and session factory for chat persistence."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.chat_models import Base

logger = logging.getLogger(__name__)

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _database_url_raw() -> str:
    return (os.getenv("DATABASE_URL") or os.getenv("REGULATORY_DATABASE_URL") or "").strip()


def chat_persistence_enabled() -> bool:
    raw = (os.getenv("CHAT_PERSISTENCE_ENABLED") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if raw in ("1", "true", "yes", "on"):
        return bool(_database_url_raw())
    return bool(_database_url_raw())


def database_url() -> str | None:
    u = _database_url_raw()
    return u or None


def _normalize_async_url(url: str) -> str:
    if url.startswith("postgresql://") and "+asyncpg" not in url.split("://", 1)[0]:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def _append_asyncpg_ssl_if_rds(url: str) -> str:
    """RDS requires TLS. asyncpg (via SQLAlchemy URL query) needs sslmode=require, not ssl=true.

    ``ssl=true`` is interpreted as an invalid sslmode token and raises ClientConfigurationError.
    """
    raw = (os.getenv("CHAT_DB_SSL") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return url
    if ".rds.amazonaws.com" not in url:
        return url
    parsed = urlparse(url)
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    keys_lower = {k.lower() for k, _ in pairs}
    if "sslmode" in keys_lower:
        return url
    # Remove mistaken ``ssl=`` pairs (e.g. legacy ssl=true); they are not valid asyncpg sslmodes.
    pairs = [(k, v) for k, v in pairs if k.lower() != "ssl"]
    pairs.append(("sslmode", "require"))
    new_query = urlencode(pairs)
    rebuilt = urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment)
    )
    return rebuilt


def chat_db_pool_ready() -> bool:
    return _session_factory is not None


async def init_chat_database() -> None:
    global _engine, _session_factory
    if _engine is not None:
        return
    if not chat_persistence_enabled():
        logger.info("Chat persistence disabled (CHAT_PERSISTENCE_ENABLED=false or no DATABASE_URL).")
        return
    url = database_url()
    if not url:
        return
    nurl = _append_asyncpg_ssl_if_rds(_normalize_async_url(url))
    _engine = create_async_engine(
        nurl,
        pool_pre_ping=True,
        pool_size=int(os.getenv("CHAT_DB_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("CHAT_DB_MAX_OVERFLOW", "5")),
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False, autoflush=False)
    if os.getenv("CHAT_AUTO_CREATE_SCHEMA", "").strip().lower() in ("1", "true", "yes"):
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("CHAT_AUTO_CREATE_SCHEMA: applied create_all for chat tables.")
    logger.info("Chat persistence database engine ready.")


async def dispose_chat_database() -> None:
    global _engine, _session_factory
    if _engine is None:
        return
    await _engine.dispose()
    _engine = None
    _session_factory = None


def session_factory() -> async_sessionmaker[AsyncSession] | None:
    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        raise RuntimeError("Database not initialized")
    async with _session_factory() as session:
        yield session
