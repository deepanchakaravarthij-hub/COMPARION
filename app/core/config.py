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


def _get_float(name: str, default: float) -> float:
    value = getenv(name)
    if value is None:
        return default
    return float(value)


def _get_bool(name: str, default: bool) -> bool:
    value = getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


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
    preprocessing_enabled: bool = _get_bool("COMPARION_PREPROCESSING_ENABLED", True)
    ocr_enabled: bool = _get_bool("COMPARION_OCR_ENABLED", True)
    ocr_adapter: str = getenv("COMPARION_OCR_ADAPTER", "none")
    ocr_confidence_threshold: float = _get_float("COMPARION_OCR_CONFIDENCE_THRESHOLD", 0.6)
    ocr_language: str = getenv("COMPARION_OCR_LANGUAGE", "en")
    alignment_enabled: bool = _get_bool("COMPARION_ALIGNMENT_ENABLED", True)
    ecc_alignment_enabled: bool = _get_bool("COMPARION_ECC_ALIGNMENT_ENABLED", False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
