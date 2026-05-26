from __future__ import annotations

from difflib import SequenceMatcher
from io import BytesIO
from typing import Any

import fitz  # type: ignore[import-untyped]
from PIL import Image

_MAX_PAGES = 10


def extract_text(content: bytes) -> str:
    with fitz.open(stream=content, filetype="pdf") as document:
        return "\n".join(page.get_text("text") for page in document)


def render_pages(content: bytes, max_pages: int = _MAX_PAGES) -> list[Image.Image]:
    images: list[Image.Image] = []
    with fitz.open(stream=content, filetype="pdf") as document:
        for page_number in range(min(document.page_count, max_pages)):
            page = document.load_page(page_number)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            image = Image.open(BytesIO(pixmap.tobytes("png"))).convert("L")
            images.append(image)
    return images


def extract_page_words(content: bytes, max_pages: int = _MAX_PAGES) -> list[list[dict[str, Any]]]:
    """Extract words with normalized (0–1) bounding boxes per page."""
    pages: list[list[dict[str, Any]]] = []
    with fitz.open(stream=content, filetype="pdf") as document:
        for page_idx in range(min(document.page_count, max_pages)):
            page = document.load_page(page_idx)
            rect = page.rect
            pw, ph = rect.width, rect.height
            if pw <= 0 or ph <= 0:
                pages.append([])
                continue
            word_data: list[dict[str, Any]] = []
            for item in page.get_text("words"):
                x0, y0, x1, y1, text = item[0], item[1], item[2], item[3], item[4]
                clean = str(text).strip()
                if not clean:
                    continue
                word_data.append(
                    {
                        "text": clean,
                        "x": x0 / pw,
                        "y": y0 / ph,
                        "w": (x1 - x0) / pw,
                        "h": (y1 - y0) / ph,
                    }
                )
            pages.append(word_data)
    return pages


def _merge_word_boxes(words: list[dict[str, Any]]) -> dict[str, float]:
    x0 = min(w["x"] for w in words)
    y0 = min(w["y"] for w in words)
    x1 = max(w["x"] + w["w"] for w in words)
    y1 = max(w["y"] + w["h"] for w in words)
    return {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}


def word_diff_page(
    words_a: list[dict[str, Any]],
    words_b: list[dict[str, Any]],
    page: int,
) -> list[dict[str, Any]]:
    """Diff two pages word-by-word; returns change dicts with normalized bboxes."""
    texts_a = [w["text"] for w in words_a]
    texts_b = [w["text"] for w in words_b]
    changes: list[dict[str, Any]] = []
    matcher = SequenceMatcher(a=texts_a, b=texts_b, autojunk=False)
    for tag, a0, a1, b0, b1 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag in ("replace", "delete"):
            run = words_a[a0:a1]
            if run:
                changes.append(
                    {
                        "type": "removed",
                        "category": "text",
                        "severity": "medium",
                        "confidence": 0.9,
                        "message": "Text removed: " + repr(" ".join(w["text"] for w in run)),
                        "source_ref": {"document": "a", "page": page},
                        "bbox": {"page": page, **_merge_word_boxes(run)},
                    }
                )
        if tag in ("replace", "insert"):
            run = words_b[b0:b1]
            if run:
                changes.append(
                    {
                        "type": "added",
                        "category": "text",
                        "severity": "medium",
                        "confidence": 0.9,
                        "message": "Text added: " + repr(" ".join(w["text"] for w in run)),
                        "source_ref": {"document": "b", "page": page},
                        "bbox": {"page": page, **_merge_word_boxes(run)},
                    }
                )
    return changes
