from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id         = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name       = mapped_column(String, nullable=False)
    slug       = mapped_column(String, unique=True, index=True, nullable=False)
    plan       = mapped_column(String, default="free", nullable=False)  # free | starter | pro | enterprise
    is_active  = mapped_column(Boolean, default=True, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relations
    users: Mapped[list["User"]] = relationship("User", back_populates="tenant", lazy="noload")
