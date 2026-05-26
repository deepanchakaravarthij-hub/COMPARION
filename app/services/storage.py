from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings


class LocalStorage:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or get_settings().storage_root
        self.root.mkdir(parents=True, exist_ok=True)

    def job_dir(self, job_id: str) -> Path:
        path = self.root / "jobs" / job_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_upload(self, job_id: str, label: str, filename: str, content: bytes) -> str:
        extension = Path(filename).suffix.lower()
        path = self.job_dir(job_id) / f"{label}-{uuid4().hex}{extension}"
        path.write_bytes(content)
        return str(path)

    def save_text(self, job_id: str, filename: str, content: str) -> str:
        path = self.job_dir(job_id) / filename
        path.write_text(content, encoding="utf-8")
        return str(path)

    def save_bytes(self, job_id: str, filename: str, content: bytes) -> str:
        path = self.job_dir(job_id) / filename
        path.write_bytes(content)
        return str(path)

    def read_text(self, path: str) -> str:
        return Path(path).read_text(encoding="utf-8")


storage = LocalStorage()
