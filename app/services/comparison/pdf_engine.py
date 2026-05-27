from __future__ import annotations

import re
from difflib import SequenceMatcher
from io import BytesIO
from typing import Any

import fitz  # type: ignore[import-untyped]
from PIL import Image

_MAX_PAGES = 10
_TEXT_EQUAL_THRESHOLD = 0.88
_MIN_MATCH_SCORE = 0.35
_MAX_CENTER_DISTANCE = 0.05
_MIN_IOU = 0.08


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
    x0 = min(float(w["x"]) for w in words)
    y0 = min(float(w["y"]) for w in words)
    x1 = max(float(w["x"]) + float(w["w"]) for w in words)
    y1 = max(float(w["y"]) + float(w["h"]) for w in words)
    pad_x = max(0.001, (x1 - x0) * 0.04)
    pad_y = max(0.001, (y1 - y0) * 0.08)
    x0 = max(0.0, x0 - pad_x)
    y0 = max(0.0, y0 - pad_y)
    x1 = min(1.0, x1 + pad_x)
    y1 = min(1.0, y1 + pad_y)
    return {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0}


def _word_bounds(word: dict[str, Any]) -> tuple[float, float, float, float]:
    x0 = float(word["x"])
    y0 = float(word["y"])
    return x0, y0, x0 + float(word["w"]), y0 + float(word["h"])


def _word_center(word: dict[str, Any]) -> tuple[float, float]:
    x0, y0, x1, y1 = _word_bounds(word)
    return (x0 + x1) / 2, (y0 + y1) / 2


def _box_iou(word_a: dict[str, Any], word_b: dict[str, Any]) -> float:
    ax0, ay0, ax1, ay1 = _word_bounds(word_a)
    bx0, by0, bx1, by1 = _word_bounds(word_b)
    ix0 = max(ax0, bx0)
    iy0 = max(ay0, by0)
    ix1 = min(ax1, bx1)
    iy1 = min(ay1, by1)
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter = (ix1 - ix0) * (iy1 - iy0)
    area_a = (ax1 - ax0) * (ay1 - ay0)
    area_b = (bx1 - bx0) * (by1 - by0)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _center_distance(word_a: dict[str, Any], word_b: dict[str, Any]) -> float:
    ax, ay = _word_center(word_a)
    bx, by = _word_center(word_b)
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5


def _normalize_token(text: str) -> str:
    return re.sub(r"[^\w\s]", "", str(text).lower()).strip()


def _text_similarity(left: str, right: str) -> float:
    left_norm = _normalize_token(left)
    right_norm = _normalize_token(right)
    if left_norm == right_norm:
        return 1.0
    if not left_norm or not right_norm:
        return 0.0
    return SequenceMatcher(a=left_norm, b=right_norm, autojunk=False).ratio()


def _match_score(word_a: dict[str, Any], word_b: dict[str, Any]) -> float:
    iou = _box_iou(word_a, word_b)
    center_dist = _center_distance(word_a, word_b)
    if iou < _MIN_IOU and center_dist > _MAX_CENTER_DISTANCE:
        return 0.0
    text_sim = _text_similarity(str(word_a["text"]), str(word_b["text"]))
    spatial = max(iou, max(0.0, 1.0 - center_dist / _MAX_CENTER_DISTANCE))
    return spatial * 0.55 + text_sim * 0.45


def _spatial_word_pairs(
    words_a: list[dict[str, Any]],
    words_b: list[dict[str, Any]],
) -> tuple[list[tuple[int, int]], set[int], set[int]]:
    candidates: list[tuple[float, int, int]] = []
    for index_a, word_a in enumerate(words_a):
        for index_b, word_b in enumerate(words_b):
            score = _match_score(word_a, word_b)
            if score >= _MIN_MATCH_SCORE:
                candidates.append((score, index_a, index_b))
    candidates.sort(reverse=True)

    matched_a: set[int] = set()
    matched_b: set[int] = set()
    pairs: list[tuple[int, int]] = []
    for _, index_a, index_b in candidates:
        if index_a in matched_a or index_b in matched_b:
            continue
        pairs.append((index_a, index_b))
        matched_a.add(index_a)
        matched_b.add(index_b)
    return pairs, matched_a, matched_b


def _text_change(
    change_type: str,
    document: str,
    words: list[dict[str, Any]],
    page: int,
    message: str,
) -> dict[str, Any]:
    return {
        "type": change_type,
        "category": "text",
        "severity": "medium",
        "confidence": 0.9,
        "message": message,
        "source_ref": {"document": document, "page": page},
        "bbox": {"page": page, **_merge_word_boxes(words)},
    }


def word_diff_page(
    words_a: list[dict[str, Any]],
    words_b: list[dict[str, Any]],
    page: int,
) -> list[dict[str, Any]]:
    """Diff words by spatial position first, then text similarity."""
    if not words_a and not words_b:
        return []

    pairs, matched_a, matched_b = _spatial_word_pairs(words_a, words_b)
    changes: list[dict[str, Any]] = []

    for index_a, index_b in pairs:
        word_a = words_a[index_a]
        word_b = words_b[index_b]
        similarity = _text_similarity(str(word_a["text"]), str(word_b["text"]))
        if similarity >= _TEXT_EQUAL_THRESHOLD:
            continue
        left_text = str(word_a["text"])
        right_text = str(word_b["text"])
        changes.append(
            _text_change(
                "removed",
                "a",
                [word_a],
                page,
                f"Text modified: {left_text!r} -> {right_text!r}",
            )
        )
        changes.append(
            _text_change(
                "added",
                "b",
                [word_b],
                page,
                f"Text modified: {left_text!r} -> {right_text!r}",
            )
        )

    for index_a, word_a in enumerate(words_a):
        if index_a in matched_a:
            continue
        changes.append(
            _text_change(
                "removed",
                "a",
                [word_a],
                page,
                "Text removed: " + repr(str(word_a["text"])),
            )
        )

    for index_b, word_b in enumerate(words_b):
        if index_b in matched_b:
            continue
        changes.append(
            _text_change(
                "added",
                "b",
                [word_b],
                page,
                "Text added: " + repr(str(word_b["text"])),
            )
        )

    changes.sort(
        key=lambda change: (
            float(change.get("bbox", {}).get("y", 0)),
            float(change.get("bbox", {}).get("x", 0)),
        )
    )
    return changes
