from __future__ import annotations

import time
from typing import Any

from PIL import Image

from app.core.config import get_settings
from app.services.benchmarking import summarize_metrics
from app.services.comparison.alignment import (
    align_to_reference,
    alignment_diagnostics,
    refine_with_ecc,
)
from app.services.comparison.debug_artifacts import debug_artifact, save_debug_image
from app.services.comparison.docx_engine import compare_docx_documents
from app.services.comparison.image_engine import load_normalized_image, visual_change
from app.services.comparison.ocr import filter_tokens, get_ocr_engine
from app.services.comparison.pdf_engine import (
    extract_page_words,
    extract_text,
    render_pages,
    word_diff_page,
)
from app.services.comparison.pptx_engine import compare_pptx_presentations
from app.services.comparison.preprocessing import PreprocessedImage, preprocess_image
from app.services.comparison.text_diff import token_changes
from app.services.comparison.xlsx_engine import compare_xlsx_workbooks
from app.services.semantic import SemanticOptions, apply_semantic_layer
from app.utils.filetype import detect_type

RESULT_SCHEMA_VERSION = "2.1"


def compare_files(
    file_a_name: str,
    file_b_name: str,
    content_a: bytes,
    content_b: bytes,
    job_id: str | None = None,
) -> dict[str, Any]:
    started_at = time.perf_counter()
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
            diagnostics=_diagnostics(started_at, [], [], [], change_count=1),
        )

    if type_a == "pdf":
        return _compare_pdf(content_a, content_b, job_id, started_at)
    if type_a == "image":
        return _compare_image(content_a, content_b, job_id, started_at)
    if type_a == "docx":
        return _compare_docx(content_a, content_b, started_at)
    if type_a == "xlsx":
        return _compare_xlsx(content_a, content_b, started_at)
    if type_a == "pptx":
        return _compare_pptx(content_a, content_b, started_at)

    return _result(
        summary=f"Unsupported file type for Sprint 2 baseline: {type_a}",
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
        diagnostics=_diagnostics(started_at, [], [], [], change_count=1),
    )


def _compare_pdf(
    content_a: bytes,
    content_b: bytes,
    job_id: str | None,
    started_at: float,
) -> dict[str, Any]:
    changes: list[dict[str, Any]] = []
    preprocessing: list[dict[str, Any]] = []
    alignments: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    ocr_confidences: list[float] = []

    pages_a = render_pages(content_a)
    pages_b = render_pages(content_b)
    word_pages_a = extract_page_words(content_a)
    word_pages_b = extract_page_words(content_b)

    max_pages = max(len(pages_a), len(pages_b))
    for index in range(max_pages):
        page = index + 1
        if index >= len(pages_a) or index >= len(pages_b):
            changes.append(
                _change(
                    "modified",
                    "metadata",
                    "high",
                    1.0,
                    f"Page count differs at page {page}",
                    "both",
                    page=page,
                )
            )
            continue

        # Per-page word-level text diff with normalized bounding boxes
        wa = word_pages_a[index] if index < len(word_pages_a) else []
        wb = word_pages_b[index] if index < len(word_pages_b) else []
        if wa or wb:
            changes.extend(word_diff_page(wa, wb, page))
        else:
            # Scanned/image-only page — fall back to OCR token diff (no spatial positions)
            text_a = extract_text(content_a)
            text_b = extract_text(content_b)
            if not text_a.strip() and pages_a:
                text_a, confidence_a = _ocr_text(pages_a[index])
                ocr_confidences.append(confidence_a)
            if not text_b.strip() and pages_b:
                text_b, confidence_b = _ocr_text(pages_b[index])
                ocr_confidences.append(confidence_b)
            changes.extend(token_changes(text_a, text_b))

        processed_a, processed_b, page_preprocessing = _prepare_pair(pages_a[index], pages_b[index])
        preprocessing.extend(_page_metadata(page, page_preprocessing))
        aligned_b, alignment = _align_pair(processed_a.image, processed_b.image)
        alignments.append(alignment_diagnostics(alignment, page))
        artifact = debug_artifact(
            save_debug_image(job_id, f"page-{page}-aligned-b.png", aligned_b),
            "aligned_candidate",
            page,
        )
        if artifact:
            artifacts.append(artifact)

        visual = visual_change(processed_a.image, aligned_b, page=page)
        if visual:
            changes.append(visual)

    return _result(
        summary=_summary(changes),
        file_type="pdf",
        changes=changes,
        diagnostics=_diagnostics(
            started_at,
            preprocessing,
            alignments,
            artifacts,
            ocr_confidences,
            change_count=len(changes),
        ),
    )


def _compare_image(
    content_a: bytes,
    content_b: bytes,
    job_id: str | None,
    started_at: float,
) -> dict[str, Any]:
    image_a = load_normalized_image(content_a)
    image_b = load_normalized_image(content_b)
    processed_a, processed_b, preprocessing = _prepare_pair(image_a, image_b)
    aligned_b, alignment = _align_pair(processed_a.image, processed_b.image)
    artifact = debug_artifact(
        save_debug_image(job_id, "image-aligned-b.png", aligned_b),
        "aligned_candidate",
        1,
    )
    artifacts = [artifact] if artifact else []
    visual = visual_change(processed_a.image, aligned_b)
    changes = [visual] if visual else []
    return _result(
        summary=_summary(changes),
        file_type="image",
        changes=changes,
        diagnostics=_diagnostics(
            started_at,
            _page_metadata(1, preprocessing),
            [alignment_diagnostics(alignment, 1)],
            artifacts,
            [],
            change_count=len(changes),
        ),
    )


def _compare_docx(
    content_a: bytes,
    content_b: bytes,
    started_at: float,
) -> dict[str, Any]:
    changes, docx_diagnostics = compare_docx_documents(content_a, content_b)
    diagnostics = _diagnostics(
        started_at,
        [],
        [],
        [],
        [],
        change_count=len(changes),
    )
    diagnostics["docx"] = docx_diagnostics
    return _result(
        summary=_summary(changes),
        file_type="docx",
        changes=changes,
        diagnostics=diagnostics,
    )


def _compare_xlsx(
    content_a: bytes,
    content_b: bytes,
    started_at: float,
) -> dict[str, Any]:
    changes, xlsx_diagnostics = compare_xlsx_workbooks(content_a, content_b)
    diagnostics = _diagnostics(
        started_at,
        [],
        [],
        [],
        [],
        change_count=len(changes),
    )
    diagnostics["xlsx"] = xlsx_diagnostics
    return _result(
        summary=_summary(changes),
        file_type="xlsx",
        changes=changes,
        diagnostics=diagnostics,
    )


def _compare_pptx(
    content_a: bytes,
    content_b: bytes,
    started_at: float,
) -> dict[str, Any]:
    changes, pptx_diagnostics = compare_pptx_presentations(content_a, content_b)
    diagnostics = _diagnostics(
        started_at,
        [],
        [],
        [],
        [],
        change_count=len(changes),
    )
    diagnostics["pptx"] = pptx_diagnostics
    return _result(
        summary=_summary(changes),
        file_type="pptx",
        changes=changes,
        diagnostics=diagnostics,
    )


def _prepare_pair(image_a: Image.Image, image_b: Image.Image) -> tuple[
    PreprocessedImage,
    PreprocessedImage,
    list[PreprocessedImage],
]:
    settings = get_settings()
    if not settings.preprocessing_enabled:
        processed_a = PreprocessedImage(
            image=image_a.convert("L"),
            metadata=preprocess_image(image_a, options=None).metadata,
        )
        processed_b = PreprocessedImage(
            image=image_b.convert("L"),
            metadata=preprocess_image(image_b, options=None).metadata,
        )
        return processed_a, processed_b, [processed_a, processed_b]
    processed_a = preprocess_image(image_a)
    processed_b = preprocess_image(image_b)
    return processed_a, processed_b, [processed_a, processed_b]


def _align_pair(reference: Image.Image, candidate: Image.Image) -> tuple[Image.Image, Any]:
    settings = get_settings()
    if not settings.alignment_enabled:
        alignment = align_to_reference(reference, candidate)
        return candidate.resize(reference.size), alignment
    alignment = align_to_reference(reference, candidate)
    if settings.ecc_alignment_enabled:
        alignment = refine_with_ecc(reference, alignment.image)
    return alignment.image, alignment


def _ocr_text(image: Image.Image) -> tuple[str, float]:
    settings = get_settings()
    if not settings.ocr_enabled:
        return "", 0.0
    engine = get_ocr_engine(settings.ocr_adapter, settings.ocr_language)
    result = engine.extract(image)
    tokens = [token for block in result.blocks for line in block.lines for token in line.tokens]
    filtered = filter_tokens(tokens, settings.ocr_confidence_threshold)
    if not filtered:
        return result.text, result.confidence
    text = " ".join(token.text for token in filtered)
    confidence = sum(token.confidence for token in filtered) / len(filtered)
    return text, round(confidence, 3)


def _page_metadata(page: int, processed: list[PreprocessedImage]) -> list[dict[str, Any]]:
    labels = ["a", "b"]
    metadata = []
    for index, item in enumerate(processed):
        metadata.append(
            {
                "document": labels[index],
                "page": page,
                "rotation_degrees": item.metadata.rotation_degrees,
                "skew_degrees": item.metadata.skew_degrees,
                "denoise": item.metadata.denoise,
                "threshold": item.metadata.threshold,
                "enhance_contrast": item.metadata.enhance_contrast,
            }
        )
    return metadata


def _result(
    summary: str,
    file_type: str,
    changes: list[dict[str, Any]],
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    numbered_changes = []
    for index, change in enumerate(changes, start=1):
        item = {"id": f"chg-{index:03d}", **change}
        numbered_changes.append(item)
    semantic_options = SemanticOptions(
        enabled=get_settings().semantic_enabled,
        similarity_threshold=get_settings().semantic_similarity_threshold,
        embedding_service=get_settings().embedding_model_service,
        local_summary_enabled=get_settings().local_summary_enabled,
    )
    semantic_changes, semantic_payload = apply_semantic_layer(
        numbered_changes,
        file_type,
        semantic_options,
    )
    return {
        "result_schema_version": RESULT_SCHEMA_VERSION,
        "summary": summary,
        "file_type": file_type,
        "changes": semantic_changes,
        "diagnostics": diagnostics,
        "udm": _build_udm(file_type, semantic_changes),
        "semantic": semantic_payload,
        "viewer_hints": _build_viewer_hints(file_type, semantic_changes, diagnostics),
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


def _diagnostics(
    started_at: float,
    preprocessing: list[dict[str, Any]],
    alignments: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    ocr_confidences: list[float] | None = None,
    change_count: int = 0,
) -> dict[str, Any]:
    runtime_ms = (time.perf_counter() - started_at) * 1000
    metrics = summarize_metrics(
        change_count=change_count,
        runtime_ms=runtime_ms,
        ocr_confidences=ocr_confidences or [],
    )
    return {
        "preprocessing": preprocessing,
        "alignment": alignments,
        "debug_artifacts": artifacts,
        "benchmark": {
            "change_count": metrics.change_count,
            "runtime_ms": metrics.runtime_ms,
            "ocr_confidence": metrics.ocr_confidence,
            "false_positive_count": metrics.false_positive_count,
        },
    }


def _build_udm(file_type: str, changes: list[dict[str, Any]]) -> dict[str, Any]:
    blocks = []
    for change in changes:
        message = change.get("message", "")
        block_type = _udm_block_type(change.get("category", ""))
        bbox = change.get("bbox")
        blocks.append(
            {
                "block_id": change["id"],
                "type": block_type,
                "category": change.get("category", "unknown"),
                "change_type": change.get("type", "modified"),
                "severity": change.get("severity", "medium"),
                "confidence": change.get("confidence", 0.0),
                "text": message if isinstance(message, str) else None,
                "source_ref": change.get("source_ref", {}),
                "bbox": bbox,
            }
        )
    return {
        "schema_version": "1.0",
        "documents": [
            {
                "doc_id": "a",
                "version_id": "current",
                "format": file_type,
                "blocks": blocks,
            }
        ],
    }


def _udm_block_type(category: str) -> str:
    if category in {"text", "formula"}:
        return "text"
    if category == "table":
        return "table"
    if category == "image":
        return "image"
    if category in {"structure", "sheet", "slide"}:
        return "structure"
    if category in {"metadata", "visual", "formatting"}:
        return "metadata"
    return "unknown"


def _build_viewer_hints(
    file_type: str,
    changes: list[dict[str, Any]],
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    refs = [change.get("source_ref", {}) for change in changes]
    categories = sorted({str(change.get("category", "unknown")) for change in changes})
    severities = sorted({str(change.get("severity", "medium")) for change in changes})
    anchors = {
        "pages": sorted({ref["page"] for ref in refs if ref.get("page") is not None}),
        "slides": sorted({ref["slide"] for ref in refs if ref.get("slide") is not None}),
        "sheets": sorted({ref["sheet"] for ref in refs if ref.get("sheet") is not None}),
        "cells": sorted({ref["cell"] for ref in refs if ref.get("cell") is not None}),
    }
    return {
        "coordinate_policy": "normalized_0_to_1",
        "artifact_labels": ["a", "b"],
        "renderer": _renderer_hint(file_type),
        "anchors": anchors,
        "filters": {
            "categories": categories,
            "severities": severities,
            "semantic_labels": sorted(
                {
                    str(change.get("semantic_label"))
                    for change in changes
                    if change.get("semantic_label") is not None
                }
            ),
        },
        "counts": _viewer_counts(file_type, diagnostics),
    }


def _renderer_hint(file_type: str) -> dict[str, Any]:
    if file_type == "pdf":
        return {"type": "pdf", "supports_overlays": True, "primary_axis": "page"}
    if file_type == "image":
        return {"type": "image", "supports_overlays": True, "primary_axis": "page"}
    if file_type == "docx":
        return {"type": "docx", "supports_overlays": False, "primary_axis": "paragraph"}
    if file_type == "xlsx":
        return {"type": "xlsx", "supports_overlays": False, "primary_axis": "sheet"}
    if file_type == "pptx":
        return {"type": "pptx", "supports_overlays": True, "primary_axis": "slide"}
    return {"type": file_type, "supports_overlays": False, "primary_axis": "change"}


def _viewer_counts(file_type: str, diagnostics: dict[str, Any]) -> dict[str, Any]:
    if file_type == "docx":
        docx_counts = diagnostics.get("docx", {})
        return docx_counts if isinstance(docx_counts, dict) else {}
    if file_type == "xlsx":
        xlsx_counts = diagnostics.get("xlsx", {})
        if isinstance(xlsx_counts, dict):
            sheet_count = xlsx_counts.get("sheet_count", {})
            return sheet_count if isinstance(sheet_count, dict) else {}
        return {}
    if file_type == "pptx":
        pptx_counts = diagnostics.get("pptx", {})
        if isinstance(pptx_counts, dict):
            slide_count = pptx_counts.get("slide_count", {})
            return slide_count if isinstance(slide_count, dict) else {}
        return {}
    benchmark = diagnostics.get("benchmark", {})
    if isinstance(benchmark, dict):
        return {"change_count": benchmark.get("change_count", 0)}
    return {"change_count": 0}
