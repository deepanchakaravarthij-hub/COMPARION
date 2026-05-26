from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from os import getenv
from pathlib import Path


def _get_int(name: str, default: int) -> int:
    value = getenv(name)
    if value is None:
        return default
    return int(value)


@dataclass(frozen=True)
class Settings:
    app_name: str = getenv("COMPARION_APP_NAME", "COMPARION API")
    environment: str = getenv("COMPARION_ENVIRONMENT", "local")
    log_level: str = getenv("COMPARION_LOG_LEVEL", "INFO")
    max_upload_mb: int = _get_int("COMPARION_MAX_UPLOAD_MB", 50)
    database_url: str = getenv(
        "COMPARION_DATABASE_URL",
        "sqlite:///storage/comparion.db",
    )
    storage_root: Path = Path(getenv("COMPARION_STORAGE_ROOT", "storage"))
    redis_url: str = getenv("COMPARION_REDIS_URL", "redis://localhost:6379/0")
    storage_endpoint: str = getenv("COMPARION_STORAGE_ENDPOINT", "http://localhost:9000")
    storage_bucket: str = getenv("COMPARION_STORAGE_BUCKET", "comparion")


@lru_cache
def get_settings() -> Settings:
    return Settings()
