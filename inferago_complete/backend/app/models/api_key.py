import uuid, secrets
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class ApiKey(Base):
    __tablename__ = "api_keys"
    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    key          = Column(String, unique=True, index=True, nullable=False)
    name         = Column(String, nullable=False)
    is_active    = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @staticmethod
    def generate_key() -> str:
        return f"inf_live_{secrets.token_urlsafe(32)}"
