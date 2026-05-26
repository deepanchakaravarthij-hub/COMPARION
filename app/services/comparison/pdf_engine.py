from __future__ import annotations

from io import BytesIO

import fitz  # type: ignore[import-untyped]
from PIL import Image


def extract_text(content: bytes) -> str:
    with fitz.open(stream=content, filetype="pdf") as document:
        return "\n".join(page.get_text("text") for page in document)


def render_pages(content: bytes, max_pages: int = 10) -> list[Image.Image]:
    images: list[Image.Image] = []
    with fitz.open(stream=content, filetype="pdf") as document:
        for page_number in range(min(document.page_count, max_pages)):
            page = document.load_page(page_number)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            image = Image.open(BytesIO(pixmap.tobytes("png"))).convert("L")
            images.append(image)
    return images
