from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_user: str = os.getenv("POSTGRES_USER", "store")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "storepass")
    postgres_host: str = os.getenv("POSTGRES_HOST", "postgres")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "store_intel")

    redis_host: str = os.getenv("REDIS_HOST", "redis")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    event_stream: str = os.getenv("EVENT_STREAM", "store.events")
    consumer_group: str = os.getenv("CONSUMER_GROUP", "backend-consumers")

    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    config_dir: str = os.getenv("CONFIG_DIR", "/configs")

    @property
    def dsn(self) -> str:
        return (f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}")

    def zones(self) -> dict[str, Any]:
        p = Path(self.config_dir) / "zones.yaml"
        if not p.exists():
            return {}
        return yaml.safe_load(p.read_text()) or {}


settings = Settings()
