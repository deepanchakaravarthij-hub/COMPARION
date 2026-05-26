from __future__ import annotations

import hashlib
import subprocess

from fastapi import HTTPException, UploadFile

from app.core.config import get_settings
from app.utils.filetype import detect_type

SUPPORTED_TYPES = {"pdf", "image", "docx", "xlsx", "pptx"}
SUPPORTED_MIME_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "image/png": "image",
    "image/jpeg": "image",
    "image/tiff": "image",
    "image/bmp": "image",
    "image/webp": "image",
}
SUSPICIOUS_MAGIC_HEADERS = [
    b"MZ",  # Windows executable
    b"\x7fELF",  # Linux binary
]


class ValidatedUpload:
    def __init__(
        self,
        filename: str,
        content_type: str,
        file_type: str,
        content: bytes,
        sha256: str,
    ) -> None:
        self.filename = filename
        self.content_type = content_type
        self.file_type = file_type
        self.content = content
        self.sha256 = sha256


async def validate_upload(upload: UploadFile) -> ValidatedUpload:
    if not upload.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must include a filename")

    content = await upload.read()
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded file exceeds {get_settings().max_upload_mb} MB limit",
        )

    file_type = detect_type(upload.filename)
    if file_type not in SUPPORTED_TYPES:
        raise HTTPException(status_code=415, detail=f"Unsupported file extension: {file_type}")

    content_type = upload.content_type or "application/octet-stream"
    expected_type = SUPPORTED_MIME_TYPES.get(content_type)
    if expected_type is not None and expected_type != file_type:
        raise HTTPException(status_code=415, detail="File extension and MIME type do not match")

    _scan_for_malware(content)

    return ValidatedUpload(
        filename=upload.filename,
        content_type=content_type,
        file_type=file_type,
        content=content,
        sha256=hashlib.sha256(content).hexdigest(),
    )


def _scan_for_malware(content: bytes) -> None:
    settings = get_settings()
    if any(content.startswith(header) for header in SUSPICIOUS_MAGIC_HEADERS):
        raise HTTPException(status_code=400, detail="Blocked suspicious binary upload")
    if not settings.malware_scan_enabled or not settings.malware_scan_command:
        return

    command = settings.malware_scan_command
    try:
        result = subprocess.run(
            command,
            input=content,
            capture_output=True,
            shell=True,
            check=False,
        )
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Malware scan hook failed: {exc}") from exc

    if result.returncode != 0:
        raise HTTPException(status_code=400, detail="Malware scan rejected upload")
