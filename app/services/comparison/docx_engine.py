from __future__ import annotations

from collections import Counter
from difflib import SequenceMatcher
from typing import Any

from app.services.comparison.docx_parser import (
    DocxDocumentModel,
    DocxParagraph,
    DocxRun,
    DocxTable,
    parse_docx,
)


def compare_docx_documents(
    content_a: bytes,
    content_b: bytes,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    document_a = parse_docx(content_a, "a")
    document_b = parse_docx(content_b, "b")

    changes: list[dict[str, Any]] = []
    changes.extend(_paragraph_text_changes(document_a.paragraphs, document_b.paragraphs))
    changes.extend(_run_text_changes(document_a.paragraphs, document_b.paragraphs))
    changes.extend(_formatting_changes(document_a.paragraphs, document_b.paragraphs))
    changes.extend(_table_changes(document_a.tables, document_b.tables))
    changes.extend(_image_changes(document_a, document_b))
    changes.extend(_move_changes(document_a.paragraphs, document_b.paragraphs))

    diagnostics = {
        "paragraph_count": {"a": len(document_a.paragraphs), "b": len(document_b.paragraphs)},
        "table_count": {"a": len(document_a.tables), "b": len(document_b.tables)},
        "image_count": {"a": len(document_a.images), "b": len(document_b.images)},
    }
    return changes, diagnostics


def _paragraph_text_changes(
    paragraphs_a: list[DocxParagraph],
    paragraphs_b: list[DocxParagraph],
) -> list[dict[str, Any]]:
    texts_a = [paragraph.normalized_text for paragraph in paragraphs_a]
    texts_b = [paragraph.normalized_text for paragraph in paragraphs_b]
    changes: list[dict[str, Any]] = []

    matcher = SequenceMatcher(a=texts_a, b=texts_b, autojunk=False)
    for tag, a_start, a_end, b_start, b_end in matcher.get_opcodes():
        if tag == "equal":
            continue

        if tag == "replace" and (a_end - a_start) == (b_end - b_start):
            for offset in range(a_end - a_start):
                old_text = texts_a[a_start + offset]
                new_text = texts_b[b_start + offset]
                if old_text == new_text:
                    continue
                changes.append(
                    _change(
                        "modified",
                        "text",
                        "medium",
                        0.92,
                        f"Paragraph text modified: {old_text!r} -> {new_text!r}",
                        _both_ref(paragraphs_a[a_start + offset].source_ref),
                    )
                )
            continue

        for paragraph in paragraphs_a[a_start:a_end]:
            if paragraph.normalized_text:
                changes.append(
                    _change(
                        "removed",
                        "text",
                        "medium",
                        0.9,
                        f"Paragraph removed: {paragraph.normalized_text!r}",
                        paragraph.source_ref,
                    )
                )
        for paragraph in paragraphs_b[b_start:b_end]:
            if paragraph.normalized_text:
                changes.append(
                    _change(
                        "added",
                        "text",
                        "medium",
                        0.9,
                        f"Paragraph added: {paragraph.normalized_text!r}",
                        paragraph.source_ref,
                    )
                )

    return changes


def _formatting_changes(
    paragraphs_a: list[DocxParagraph],
    paragraphs_b: list[DocxParagraph],
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for paragraph_a, paragraph_b in zip(paragraphs_a, paragraphs_b, strict=False):
        if (
            not paragraph_a.normalized_text
            or paragraph_a.normalized_text != paragraph_b.normalized_text
        ):
            continue

        if paragraph_a.style.signature() != paragraph_b.style.signature():
            changes.append(
                _change(
                    "modified",
                    "formatting",
                    "low",
                    0.86,
                    f"Paragraph formatting modified: {paragraph_a.normalized_text!r}",
                    _both_ref(paragraph_a.source_ref),
                )
            )

        changes.extend(_run_formatting_changes(paragraph_a.runs, paragraph_b.runs))
    return changes


def _run_text_changes(
    paragraphs_a: list[DocxParagraph],
    paragraphs_b: list[DocxParagraph],
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for paragraph_a, paragraph_b in zip(paragraphs_a, paragraphs_b, strict=False):
        if paragraph_a.normalized_text == paragraph_b.normalized_text:
            continue

        max_runs = max(len(paragraph_a.runs), len(paragraph_b.runs))
        for run_index in range(max_runs):
            run_a = paragraph_a.runs[run_index] if run_index < len(paragraph_a.runs) else None
            run_b = paragraph_b.runs[run_index] if run_index < len(paragraph_b.runs) else None
            text_a = _normalized_run_text(run_a)
            text_b = _normalized_run_text(run_b)
            if text_a == text_b:
                continue

            if run_a is None and run_b is not None:
                changes.append(
                    _change(
                        "added",
                        "text",
                        "medium",
                        0.88,
                        f"Run text added: {text_b!r}",
                        run_b.source_ref,
                    )
                )
            elif run_b is None and run_a is not None:
                changes.append(
                    _change(
                        "removed",
                        "text",
                        "medium",
                        0.88,
                        f"Run text removed: {text_a!r}",
                        run_a.source_ref,
                    )
                )
            elif run_a is not None:
                changes.append(
                    _change(
                        "modified",
                        "text",
                        "medium",
                        0.88,
                        f"Run text modified: {text_a!r} -> {text_b!r}",
                        _both_ref(run_a.source_ref),
                    )
                )
    return changes


def _run_formatting_changes(
    runs_a: list[DocxRun],
    runs_b: list[DocxRun],
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for run_a, run_b in zip(runs_a, runs_b, strict=False):
        text_a = " ".join(run_a.text.split())
        text_b = " ".join(run_b.text.split())
        if not text_a or text_a != text_b:
            continue
        if run_a.style.signature() == run_b.style.signature():
            continue
        changes.append(
            _change(
                "modified",
                "formatting",
                "low",
                0.88,
                f"Run formatting modified: {text_a!r}",
                _both_ref(run_a.source_ref),
            )
        )
    return changes


def _normalized_run_text(run: DocxRun | None) -> str:
    if run is None:
        return ""
    return " ".join(run.text.split())


def _table_changes(
    tables_a: list[DocxTable],
    tables_b: list[DocxTable],
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    max_tables = max(len(tables_a), len(tables_b))
    for table_index in range(max_tables):
        if table_index >= len(tables_a):
            changes.append(
                _change(
                    "added",
                    "table",
                    "high",
                    0.94,
                    f"Table added at index {table_index + 1}",
                    tables_b[table_index].source_ref,
                )
            )
            continue
        if table_index >= len(tables_b):
            changes.append(
                _change(
                    "removed",
                    "table",
                    "high",
                    0.94,
                    f"Table removed at index {table_index + 1}",
                    tables_a[table_index].source_ref,
                )
            )
            continue
        changes.extend(_single_table_changes(tables_a[table_index], tables_b[table_index]))
    return changes


def _single_table_changes(table_a: DocxTable, table_b: DocxTable) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    if len(table_a.rows) != len(table_b.rows):
        changes.append(
            _change(
                "modified",
                "table",
                "high",
                0.93,
                f"Table row count modified: {len(table_a.rows)} -> {len(table_b.rows)}",
                _both_ref(table_a.source_ref),
            )
        )

    max_rows = max(len(table_a.rows), len(table_b.rows))
    for row_index in range(max_rows):
        row_a = table_a.rows[row_index] if row_index < len(table_a.rows) else []
        row_b = table_b.rows[row_index] if row_index < len(table_b.rows) else []
        if len(row_a) != len(row_b):
            changes.append(
                _change(
                    "modified",
                    "table",
                    "high",
                    0.92,
                    f"Table column count modified at row {row_index + 1}: "
                    f"{len(row_a)} -> {len(row_b)}",
                    _both_ref(table_a.source_ref),
                )
            )

        max_columns = max(len(row_a), len(row_b))
        for column_index in range(max_columns):
            if column_index >= len(row_a):
                changes.append(
                    _change(
                        "added",
                        "table",
                        "medium",
                        0.92,
                        f"Table cell added: {row_b[column_index].normalized_text!r}",
                        row_b[column_index].source_ref,
                    )
                )
                continue
            if column_index >= len(row_b):
                changes.append(
                    _change(
                        "removed",
                        "table",
                        "medium",
                        0.92,
                        f"Table cell removed: {row_a[column_index].normalized_text!r}",
                        row_a[column_index].source_ref,
                    )
                )
                continue

            cell_a = row_a[column_index]
            cell_b = row_b[column_index]
            if cell_a.normalized_text != cell_b.normalized_text:
                changes.append(
                    _change(
                        "modified",
                        "table",
                        "medium",
                        0.94,
                        "Table cell modified at "
                        f"row {row_index + 1}, column {column_index + 1}: "
                        f"{cell_a.normalized_text!r} -> {cell_b.normalized_text!r}",
                        _both_ref(cell_a.source_ref),
                    )
                )
    return changes


def _image_changes(
    document_a: DocxDocumentModel,
    document_b: DocxDocumentModel,
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    if len(document_a.images) != len(document_b.images):
        changes.append(
            _change(
                "modified",
                "image",
                "medium",
                0.9,
                "Embedded image count modified: "
                f"{len(document_a.images)} -> {len(document_b.images)}",
                {"document": "both", "page": None, "part": "package"},
            )
        )

    for image_a, image_b in zip(document_a.images, document_b.images, strict=False):
        if image_a.sha256 == image_b.sha256:
            continue
        changes.append(
            _change(
                "modified",
                "image",
                "medium",
                0.95,
                f"Embedded image modified at index {image_a.source_ref['image']}",
                _both_ref(image_a.source_ref),
            )
        )
    return changes


def _move_changes(
    paragraphs_a: list[DocxParagraph],
    paragraphs_b: list[DocxParagraph],
) -> list[dict[str, Any]]:
    indexed_a = [
        (index, paragraph.normalized_text, paragraph)
        for index, paragraph in enumerate(paragraphs_a)
        if paragraph.normalized_text
    ]
    indexed_b = [
        (index, paragraph.normalized_text, paragraph)
        for index, paragraph in enumerate(paragraphs_b)
        if paragraph.normalized_text
    ]
    texts_a = [text for _, text, _ in indexed_a]
    texts_b = [text for _, text, _ in indexed_b]
    counts_b = Counter(texts_b)
    unique_texts = {
        text
        for text, count in Counter(texts_a).items()
        if count == 1 and counts_b.get(text) == 1
    }

    changes: list[dict[str, Any]] = []
    for text in sorted(unique_texts):
        old_position, _, paragraph = indexed_a[texts_a.index(text)]
        new_position, _, _ = indexed_b[texts_b.index(text)]
        if old_position == new_position:
            continue
        changes.append(
            _change(
                "modified",
                "structure",
                "medium",
                0.78,
                f"Paragraph moved: {text!r} from position {old_position + 1} "
                f"to {new_position + 1}",
                _both_ref(paragraph.source_ref),
            )
        )
    return changes


def _change(
    change_type: str,
    category: str,
    severity: str,
    confidence: float,
    message: str,
    source_ref: dict[str, Any],
) -> dict[str, Any]:
    return {
        "type": change_type,
        "category": category,
        "severity": severity,
        "confidence": confidence,
        "message": message,
        "source_ref": source_ref,
    }


def _both_ref(source_ref: dict[str, Any]) -> dict[str, Any]:
    return {**source_ref, "document": "both"}
