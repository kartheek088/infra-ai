"""
Shared utilities used across routers and services.
"""
import uuid
from typing import Any


def to_uuid(value: Any) -> uuid.UUID:
    """
    Coerce a value to a uuid.UUID for binding into SQLAlchemy UUID columns.

    FastAPI path params are typed as str, but every ID column in the schema
    (users.id, workflows.id, runs.id, alerts.id, rag_metrics.id, api_keys.id)
    is UUID(as_uuid=True). Binding a raw str triggers a parameter-encoding
    crash because asyncpg/SQLAlchemy calls .hex on the value when compiling.

    Accepts a UUID (passthrough) or a string; raises ValueError on garbage
    so we get a clean 400 instead of a 500 from the database driver.
    """
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        return uuid.UUID(value)
    raise ValueError(f"Cannot coerce {type(value).__name__} to UUID")
