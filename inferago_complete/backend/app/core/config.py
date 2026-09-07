import os
from typing import List, Union
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379"
    SECRET_KEY: str = "ari-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    CORS_ORIGINS: Union[str, List[str]] = ["*"]
    # Toggle SQL echo for debugging; defaults False so production stays clean
    DB_ECHO: bool = False
    # OpenRouter key for AI execution explanations (optional; feature degrades gracefully)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "anthropic/claude-3-haiku"

    @model_validator(mode="after")
    def validate_secret_key(self):
        """Fail fast if SECRET_KEY is the default in a non-dev environment."""
        if self.SECRET_KEY == "ari-super-secret-key-change-in-production":
            env = os.getenv("ENVIRONMENT", "development").lower()
            if env not in ("development", "dev", "test", "testing"):
                raise ValueError(
                    "SECRET_KEY is set to the default placeholder value. "
                    "Set SECRET_KEY to a cryptographically random string in production."
                )
        return self

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        if not v:
            return v
        # Supabase and Render give postgres:// or postgresql://
        # SQLAlchemy 2.0 async engine requires postgresql+asyncpg://
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


# ── Singleton instance ───────────────────────────────────────────────────────
import logging
import os as _os

settings = Settings()

_log = logging.getLogger(__name__)
if not settings.OPENROUTER_API_KEY:
    _log.warning(
        "OPENROUTER_API_KEY is not set — AI execution explanations will be "
        "unavailable. Set it in your .env file to enable the feature."
    )
env = _os.getenv("ENVIRONMENT", "development").lower()
if env not in ("development", "dev", "test", "testing"):
    if settings.SECRET_KEY == "ari-super-secret-key-change-in-production":
        _log.critical(
            "SECRET_KEY uses the default placeholder in a production environment. "
            "Set SECRET_KEY to a cryptographically random string."
        )

