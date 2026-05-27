from __future__ import annotations

from io import BytesIO

import fitz  # type: ignore[import-untyped]
from PIL import Image, ImageDraw, ImageFont

from app.services.compare_service import compare_files


def _scanned_pdf_bytes(label: str, mark: bool = False) -> bytes:
    image = Image.new("RGB", (400, 200), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.text((30, 80), f"Invoice {label}", fill="black", font=font)
    if mark:
        draw.rectangle((300, 60, 360, 120), fill="red")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    png_bytes = buffer.getvalue()

    document = fitz.open()
    page = document.new_page(width=400, height=200)
    page.insert_image(page.rect, stream=png_bytes)
    pdf_buffer = BytesIO()
    document.save(pdf_buffer)
    document.close()
    return pdf_buffer.getvalue()


def test_scanned_pdf_uses_ocr_word_diff_with_bbox() -> None:
    result = compare_files(
        "a.pdf",
        "b.pdf",
        _scanned_pdf_bytes("A"),
        _scanned_pdf_bytes("B", mark=True),
    )
    assert result["file_type"] == "pdf"
    text_changes = [change for change in result["changes"] if change.get("category") == "text"]
    assert text_changes
    assert any(change.get("bbox") for change in text_changes)
