"""
Application model — groups multiple workflows under one organizational unit.

Example: "Production", "Staging", "Dev" within a Tenant.
"""
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import String, Boolean, DateTime, ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Application(Base):
    __tablename__ = "applications"

    id          = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id   = mapped_column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    name        = mapped_column(String, nullable=False)
    description  = mapped_column(Text, nullable=True)
    environment  = mapped_column(String, default="production", nullable=False)  # production | staging | development
    is_active   = mapped_column(Boolean, default=True, nullable=False)
    created_at  = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at  = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
