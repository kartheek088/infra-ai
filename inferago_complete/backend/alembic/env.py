import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from app.db.base import Base
from app.models.user import User               # noqa
from app.models.workflow import Workflow       # noqa
from app.models.run import Run, TokenUsage    # noqa
from app.models.api_key import ApiKey         # noqa
from app.models.rag import RAGMetrics         # noqa
from app.models.alert import Alert            # noqa

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

config = context.config

# Allow override via command line; falls back to .env.
raw_url = os.environ.get("ALEMBIC_DATABASE_URL") or os.getenv("DATABASE_URL", "")
config.set_main_option("sqlalchemy.url", raw_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def _do_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Dispatches to async or sync engine based on URL scheme.

    - sqlite+aiosqlite://  → aiosqlite  (useful for dev / migration generation)
    - postgresql+asyncpg:// → asyncpg    (production)
    - postgresql://         → psycopg2  (sync fallback — needs psycopg2 installed)
    """
    url = config.get_main_option("sqlalchemy.url")

    if url.startswith("sqlite"):
        # SQLite path — use aiosqlite for async-compatible migration.
        from sqlalchemy.ext.asyncio import create_async_engine
        async_engine = create_async_engine(url, echo=False, poolclass=pool.NullPool)

        async def run_async_migrations():
            async with async_engine.connect() as connection:
                await connection.run_sync(_do_migrations)

        import asyncio
        asyncio.run(run_async_migrations())

    elif "+asyncpg" in url:
        # PostgreSQL with asyncpg — use greenlet bridge (greenlet must be installed).
        from sqlalchemy.ext.asyncio import create_async_engine
        async_engine = create_async_engine(url, echo=False, poolclass=pool.NullPool)

        async def run_async_migrations():
            async with async_engine.connect() as connection:
                await connection.run_sync(_do_migrations)

        import asyncio
        asyncio.run(run_async_migrations())

    else:
        # Plain sync PostgreSQL — use psycopg2 via engine_from_config.
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.", poolclass=pool.NullPool,
        )
        with connectable.connect() as connection:
            _do_migrations(connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
