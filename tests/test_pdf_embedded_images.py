from __future__ import annotations

from io import BytesIO

import fitz  # type: ignore[import-untyped]
from PIL import Image

from app.services.compare_service import compare_files
from app.services.comparison.pdf_engine import extract_page_images


def _pdf_with_text_and_image(*, red_square: bool) -> bytes:
    document = fitz.open()
    page = document.new_page(width=400, height=300)
    page.insert_text((40, 40), "Hello contract", fontsize=14)
    image = Image.new("RGB", (80, 80), "red" if red_square else "blue")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    page.insert_image(fitz.Rect(250, 120, 330, 200), stream=buffer.getvalue())
    pdf_buffer = BytesIO()
    document.save(pdf_buffer)
    document.close()
    return pdf_buffer.getvalue()


def test_extract_page_images_returns_bbox() -> None:
    images = extract_page_images(_pdf_with_text_and_image(red_square=True))
    assert images
    assert images[0]
    first = images[0][0]
    assert first.sha256
    assert first.bbox[2] > 0


def test_pdf_embedded_image_diff_emits_image_category() -> None:
    result = compare_files(
        "a.pdf",
        "b.pdf",
        _pdf_with_text_and_image(red_square=False),
        _pdf_with_text_and_image(red_square=True),
    )
    image_changes = [change for change in result["changes"] if change.get("category") == "image"]
    assert image_changes
    assert any(change.get("bbox") for change in image_changes)
