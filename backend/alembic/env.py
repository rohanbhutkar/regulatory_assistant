"""Alembic migrations for chat persistence (visitors, chat_sessions, chat_messages).

Run from repo root or backend/:
  export DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
  # sync driver for CLI:
  export DATABASE_URL_SYNC=postgresql://user:pass@host:5432/dbname
  cd backend && alembic upgrade head

Async URLs (postgresql+asyncpg) are rewritten to postgresql for offline/online migration runs.
"""

from logging.config import fileConfig
import os
import re

from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import Connection

from alembic import context

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from db.chat_models import Base  # noqa: E402

target_metadata = Base.metadata


def _sync_url() -> str:
    url = (
        context.get_x_argument(as_dictionary=True).get("url")
        or os.getenv("DATABASE_URL_SYNC")
        or os.getenv("DATABASE_URL")
        or os.getenv("REGULATORY_DATABASE_URL")
        or ""
    ).strip()
    if not url:
        raise RuntimeError("Set DATABASE_URL_SYNC or DATABASE_URL for alembic migrations.")
    url = re.sub(r"^postgresql\+asyncpg", "postgresql", url, count=1)
    # psycopg2 / RDS: require TLS unless CHAT_DB_SSL disables it
    raw = (os.getenv("CHAT_DB_SSL") or "").strip().lower()
    if raw not in ("0", "false", "no", "off") and ".rds.amazonaws.com" in url:
        if "sslmode=" not in url.lower():
            url = f"{url}&sslmode=require" if "?" in url else f"{url}?sslmode=require"
    return url


def run_migrations_offline() -> None:
    url = _sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    sync_url = _sync_url()
    connectable = engine_from_config(
        {"sqlalchemy.url": sync_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        do_run_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
