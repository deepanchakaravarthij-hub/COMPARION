from __future__ import annotations

from io import BytesIO
from typing import Any

from PIL import Image

from app.services.storage import storage


def save_debug_image(job_id: str | None, name: str, image: Image.Image) -> str | None:
    if job_id is None:
        return None
    output = BytesIO()
    image.save(output, format="PNG")
    return storage.save_bytes(job_id, name, output.getvalue())


def debug_artifact(path: str | None, kind: str, page: int) -> dict[str, Any] | None:
    if path is None:
        return None
    return {"kind": kind, "page": page, "path": path}
