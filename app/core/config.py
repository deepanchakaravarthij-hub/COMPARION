from __future__ import annotations

from dataclasses import dataclass, field
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


def _get_csv(name: str, default: str) -> list[str]:
    value = getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


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
    ocr_use_gpu: bool = _get_bool("COMPARION_OCR_USE_GPU", False)
    ocr_confidence_threshold: float = _get_float("COMPARION_OCR_CONFIDENCE_THRESHOLD", 0.6)
    ocr_language: str = getenv("COMPARION_OCR_LANGUAGE", "en")
    scan_word_threshold: int = _get_int("COMPARION_SCAN_WORD_THRESHOLD", 3)
    scan_force_ocr: bool = _get_bool("COMPARION_SCAN_FORCE_OCR", False)
    pdf_supplement_visual: bool = _get_bool("COMPARION_PDF_SUPPLEMENT_VISUAL", True)
    image_ssim_threshold: float = _get_float("COMPARION_IMAGE_SSIM_THRESHOLD", 0.95)
    embedded_image_max_per_page: int = _get_int("COMPARION_EMBEDDED_IMAGE_MAX_PER_PAGE", 50)
    alignment_enabled: bool = _get_bool("COMPARION_ALIGNMENT_ENABLED", True)
    ecc_alignment_enabled: bool = _get_bool("COMPARION_ECC_ALIGNMENT_ENABLED", False)
    object_storage_enabled: bool = _get_bool("COMPARION_OBJECT_STORAGE_ENABLED", False)
    signed_url_secret: str = getenv("COMPARION_SIGNED_URL_SECRET", "comparion-local-secret")
    signed_url_ttl_seconds: int = _get_int("COMPARION_SIGNED_URL_TTL_SECONDS", 900)
    semantic_enabled: bool = _get_bool("COMPARION_SEMANTIC_ENABLED", True)
    embedding_model_service: str = getenv("COMPARION_EMBEDDING_MODEL_SERVICE", "tfidf-local")
    semantic_similarity_threshold: float = _get_float(
        "COMPARION_SEMANTIC_SIMILARITY_THRESHOLD",
        0.75,
    )
    local_summary_enabled: bool = _get_bool("COMPARION_LOCAL_SUMMARY_ENABLED", True)
    auth_required: bool = _get_bool("COMPARION_AUTH_REQUIRED", False)
    auth_api_key: str = getenv("COMPARION_AUTH_API_KEY", "")
    auth_bearer_token: str = getenv("COMPARION_AUTH_BEARER_TOKEN", "")
    max_retry_attempts: int = _get_int("COMPARION_MAX_RETRY_ATTEMPTS", 3)
    retry_backoff_ms: int = _get_int("COMPARION_RETRY_BACKOFF_MS", 250)
    queue_mode: str = getenv("COMPARION_QUEUE_MODE", "inline")
    celery_broker_url: str = getenv("COMPARION_CELERY_BROKER_URL", "redis://localhost:6379/0")
    celery_result_backend: str = getenv("COMPARION_CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
    retention_days: int = _get_int("COMPARION_RETENTION_DAYS", 7)
    malware_scan_enabled: bool = _get_bool("COMPARION_MALWARE_SCAN_ENABLED", False)
    malware_scan_command: str = getenv("COMPARION_MALWARE_SCAN_COMMAND", "")
    metrics_alert_failure_rate_threshold: float = _get_float(
        "COMPARION_METRICS_ALERT_FAILURE_RATE_THRESHOLD",
        0.15,
    )
    metrics_alert_queue_depth_threshold: int = _get_int(
        "COMPARION_METRICS_ALERT_QUEUE_DEPTH_THRESHOLD",
        20,
    )
    cors_allowed_origins: list[str] = field(
        default_factory=lambda: _get_csv(
            "COMPARION_CORS_ALLOWED_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,"
            "http://localhost:3001,http://127.0.0.1:3001",
        )
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
