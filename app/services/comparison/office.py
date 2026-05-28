from __future__ import annotations

import shutil
from pathlib import Path

from app.core.config import get_settings


def soffice_executable() -> str | None:
    configured = get_settings().soffice_path.strip()
    if configured:
        path = Path(configured)
        if path.exists():
            return str(path)
    return shutil.which("soffice")


def soffice_missing_message(preview_type: str, package_hint: str) -> str:
    return (
        f"LibreOffice (soffice) is required to render {preview_type} previews. "
        "Install LibreOffice, add soffice to PATH, set COMPARION_SOFFICE_PATH, "
        f"or use the Docker image with {package_hint}."
    )
