from __future__ import annotations

from typing import Any

from app.services.comparison.image_engine import load_normalized_image, visual_change
from app.services.comparison.pdf_engine import extract_text, render_pages
from app.services.comparison.text_diff import token_changes
from app.utils.filetype import detect_type

RESULT_SCHEMA_VERSION = "1.0"


def compare_files(
    file_a_name: str,
    file_b_name: str,
    content_a: bytes,
    content_b: bytes,
) -> dict[str, Any]:
    type_a = detect_type(file_a_name)
    type_b = detect_type(file_b_name)

    if type_a != type_b:
        return _result(
            summary="File types differ; comparison cannot continue",
            file_type=f"{type_a} vs {type_b}",
            changes=[
                _change(
                    "warning",
                    "file",
                    "high",
                    1.0,
                    "Different file types uploaded",
                    "both",
                )
            ],
        )

    if type_a == "pdf":
        return _compare_pdf(content_a, content_b)
    if type_a == "image":
        return _compare_image(content_a, content_b)

    return _result(
        summary=f"Unsupported file type for Sprint 1 baseline: {type_a}",
        file_type=type_a,
        changes=[
            _change(
                "warning",
                "file",
                "medium",
                1.0,
                f"{type_a} comparison is planned for a later sprint",
                "both",
            )
        ],
    )


def _compare_pdf(content_a: bytes, content_b: bytes) -> dict[str, Any]:
    changes: list[dict[str, Any]] = []
    text_a = extract_text(content_a)
    text_b = extract_text(content_b)
    changes.extend(token_changes(text_a, text_b))

    pages_a = render_pages(content_a)
    pages_b = render_pages(content_b)
    max_pages = max(len(pages_a), len(pages_b))
    for index in range(max_pages):
        if index >= len(pages_a) or index >= len(pages_b):
            changes.append(
                _change(
                    "modified",
                    "metadata",
                    "high",
                    1.0,
                    f"Page count differs at page {index + 1}",
                    "both",
                    page=index + 1,
                )
            )
            continue
        visual = visual_change(pages_a[index], pages_b[index], page=index + 1)
        if visual:
            changes.append(visual)

    return _result(
        summary=_summary(changes),
        file_type="pdf",
        changes=changes,
    )


def _compare_image(content_a: bytes, content_b: bytes) -> dict[str, Any]:
    image_a = load_normalized_image(content_a)
    image_b = load_normalized_image(content_b)
    visual = visual_change(image_a, image_b)
    changes = [visual] if visual else []
    return _result(
        summary=_summary(changes),
        file_type="image",
        changes=changes,
    )


def _result(summary: str, file_type: str, changes: list[dict[str, Any]]) -> dict[str, Any]:
    numbered_changes = []
    for index, change in enumerate(changes, start=1):
        item = {"id": f"chg-{index:03d}", **change}
        numbered_changes.append(item)
    return {
        "result_schema_version": RESULT_SCHEMA_VERSION,
        "summary": summary,
        "file_type": file_type,
        "changes": numbered_changes,
    }


def _change(
    change_type: str,
    category: str,
    severity: str,
    confidence: float,
    message: str,
    document: str,
    page: int | None = None,
) -> dict[str, Any]:
    return {
        "type": change_type,
        "category": category,
        "severity": severity,
        "confidence": confidence,
        "message": message,
        "source_ref": {"document": document, "page": page},
    }


def _summary(changes: list[dict[str, Any]]) -> str:
    if not changes:
        return "No differences detected"
    return f"{len(changes)} difference(s) detected"
