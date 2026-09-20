from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VL_", env_file=".env", extra="ignore")

    database_url: str = "postgresql://vectorledger:vectorledger@localhost:5432/vectorledger"
    receipt_secret: str = "development-secret-change-me"
    api_key: str | None = None
    reconcile_interval_seconds: int = 60
    deletion_grace_period_seconds: int = Field(default=259_200, ge=60)
    qdrant_url: str | None = None
    qdrant_collection: str = "rag_chunks"
    qdrant_api_key: str | None = None
    redis_url: str | None = None
    target_postgres_url: str | None = None
    target_postgres_table: str = "rag_chunks"
