from __future__ import annotations

import re
import time
from io import BytesIO
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
from app.services.comparison.embedded_image import bboxes_from_changes, diff_embedded_images
from app.services.comparison.image_engine import load_normalized_image, visual_changes
from app.services.comparison.ocr import extract_ocr_words
from app.services.comparison.pdf_engine import (
    extract_page_images,
    extract_page_words,
    render_pages,
    word_diff_page,
)
from app.services.comparison.pptx_engine import compare_pptx_presentations
from app.services.comparison.preprocessing import PreprocessedImage, preprocess_image
from app.services.comparison.xlsx_engine import compare_xlsx_workbooks
from app.services.semantic import SemanticOptions, apply_semantic_layer
from app.utils.filetype import detect_type

RESULT_SCHEMA_VERSION = "2.1"
_MONTH_NAMES = "jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"
_DATE_TICK_RE = re.compile(rf"^\d{{1,2}}\s*(?:{_MONTH_NAMES})$", re.IGNORECASE)
_ROUND_AXIS_TICK_RE = re.compile(r"^-?(?:\d+|\d+\.\d+)(?:k|m|%)?$", re.IGNORECASE)


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
    settings = get_settings()
    changes: list[dict[str, Any]] = []
    preprocessing: list[dict[str, Any]] = []
    alignments: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    ocr_confidences: list[float] = []

    pages_a = render_pages(content_a)
    pages_b = render_pages(content_b)
    word_pages_a = extract_page_words(content_a)
    word_pages_b = extract_page_words(content_b)
    image_pages_a = extract_page_images(
        content_a,
        max_per_page=settings.embedded_image_max_per_page,
    )
    image_pages_b = extract_page_images(
        content_b,
        max_per_page=settings.embedded_image_max_per_page,
    )

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

        wa = word_pages_a[index] if index < len(word_pages_a) else []
        wb = word_pages_b[index] if index < len(word_pages_b) else []
        page_text_changes = _pdf_page_text_changes(
            wa,
            wb,
            page,
            pages_a[index],
            aligned_b,
            settings,
            ocr_confidences,
        )
        changes.extend(page_text_changes)

        images_a = image_pages_a[index] if index < len(image_pages_a) else []
        images_b = image_pages_b[index] if index < len(image_pages_b) else []
        changes.extend(
            diff_embedded_images(
                images_a,
                images_b,
                page=page,
                ssim_threshold=settings.image_ssim_threshold,
            )
        )

        mask_bboxes = bboxes_from_changes(page_text_changes)
        run_visual = settings.pdf_supplement_visual or not page_text_changes
        if run_visual:
            changes.extend(
                visual_changes(
                    processed_a.image,
                    aligned_b,
                    page=page,
                    mask_bboxes=mask_bboxes if settings.pdf_supplement_visual else None,
                )
            )

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
    settings = get_settings()
    image_a_rgb = Image.open(BytesIO(content_a)).convert("RGB")
    image_b_rgb = Image.open(BytesIO(content_b)).convert("RGB")
    words_a, confidence_a = extract_ocr_words(
        image_a_rgb,
        confidence_threshold=settings.ocr_confidence_threshold,
        adapter=settings.ocr_adapter,
        language=settings.ocr_language,
        enabled=settings.ocr_enabled,
    )
    words_b, confidence_b = extract_ocr_words(
        image_b_rgb,
        confidence_threshold=settings.ocr_confidence_threshold,
        adapter=settings.ocr_adapter,
        language=settings.ocr_language,
        enabled=settings.ocr_enabled,
    )
    ocr_confidences = [value for value in (confidence_a, confidence_b) if value > 0]

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

    had_ocr_words = bool(words_a or words_b)
    text_changes = word_diff_page(words_a, words_b, page=1) if had_ocr_words else []
    if settings.image_value_text_only:
        text_changes = _denoise_image_text_changes(text_changes)
    text_changes = _collapse_image_modified_pairs(text_changes)
    changes: list[dict[str, Any]] = list(text_changes)
    mask_bboxes = bboxes_from_changes(text_changes)
    if settings.image_supplement_visual or (not text_changes and not had_ocr_words):
        changes.extend(
            visual_changes(
                processed_a.image,
                aligned_b,
                page=1,
                mask_bboxes=mask_bboxes if settings.image_supplement_visual else None,
            )
        )

    return _result(
        summary=_summary(changes),
        file_type="image",
        changes=changes,
        diagnostics=_diagnostics(
            started_at,
            _page_metadata(1, preprocessing),
            [alignment_diagnostics(alignment, 1)],
            artifacts,
            ocr_confidences,
            change_count=len(changes),
        ),
    )


def _denoise_image_text_changes(changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [change for change in changes if not _is_low_signal_image_text_change(change)]


def _collapse_image_modified_pairs(changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    collapsed: list[dict[str, Any]] = []
    consumed: set[int] = set()

    for index, change in enumerate(changes):
        if index in consumed:
            continue
        pair_index = _find_image_modified_pair(index, change, changes, consumed)
        if pair_index is None:
            collapsed.append(change)
            continue

        consumed.add(index)
        consumed.add(pair_index)
        pair = changes[pair_index]
        collapsed.append(
            {
                **change,
                "type": "modified",
                "source_ref": {
                    **change.get("source_ref", {}),
                    "document": "both",
                },
                "bbox": _merge_change_bboxes(change.get("bbox"), pair.get("bbox")),
            }
        )

    return collapsed


def _find_image_modified_pair(
    index: int,
    change: dict[str, Any],
    changes: list[dict[str, Any]],
    consumed: set[int],
) -> int | None:
    if change.get("category") != "text" or not str(change.get("message", "")).startswith(
        "Text modified:"
    ):
        return None
    document = (change.get("source_ref") or {}).get("document")
    if document not in {"a", "b"}:
        return None

    other_document = "b" if document == "a" else "a"
    message = change.get("message")
    for pair_index in range(index + 1, len(changes)):
        if pair_index in consumed:
            continue
        candidate = changes[pair_index]
        if candidate.get("category") != "text":
            continue
        if candidate.get("message") != message:
            continue
        if (candidate.get("source_ref") or {}).get("document") == other_document:
            return pair_index
    return None


def _merge_change_bboxes(
    left: Any,
    right: Any,
) -> dict[str, float | int] | None:
    if not isinstance(left, dict):
        return right if isinstance(right, dict) else None
    if not isinstance(right, dict):
        return left

    x0 = min(float(left.get("x", 0.0)), float(right.get("x", 0.0)))
    y0 = min(float(left.get("y", 0.0)), float(right.get("y", 0.0)))
    x1 = max(
        float(left.get("x", 0.0)) + float(left.get("width", 0.0)),
        float(right.get("x", 0.0)) + float(right.get("width", 0.0)),
    )
    y1 = max(
        float(left.get("y", 0.0)) + float(left.get("height", 0.0)),
        float(right.get("y", 0.0)) + float(right.get("height", 0.0)),
    )
    return {
        "page": int(left.get("page") or right.get("page") or 1),
        "x": x0,
        "y": y0,
        "width": x1 - x0,
        "height": y1 - y0,
    }


def _is_low_signal_image_text_change(change: dict[str, Any]) -> bool:
    if change.get("category") != "text":
        return False

    texts = _quoted_change_texts(str(change.get("message", "")))
    if not texts:
        return False

    if not any(any(char.isdigit() for char in text) for text in texts):
        return True

    bbox = change.get("bbox") or {}
    area = float(bbox.get("width", 0.0)) * float(bbox.get("height", 0.0))
    return all(_is_chart_axis_text(text, area) for text in texts)


def _quoted_change_texts(message: str) -> list[str]:
    return [match.group(1) for match in re.finditer(r"'([^']*)'", message)]


def _is_chart_axis_text(text: str, bbox_area: float) -> bool:
    normalized = re.sub(r"\s+", "", text.strip().lower())
    if not normalized:
        return True
    if _DATE_TICK_RE.match(normalized):
        return True
    if bbox_area > 0.0009 or not _ROUND_AXIS_TICK_RE.match(normalized):
        return False
    numeric = normalized.rstrip("%km")
    try:
        value = abs(float(numeric))
    except ValueError:
        return False
    return value == 0 or value >= 5


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


def _needs_ocr(native_words: list[dict[str, Any]], settings: Any) -> bool:
    if settings.scan_force_ocr:
        return True
    return len(native_words) < settings.scan_word_threshold


def _pdf_page_text_changes(
    words_a: list[dict[str, Any]],
    words_b: list[dict[str, Any]],
    page: int,
    page_image_a: Image.Image,
    aligned_b: Image.Image,
    settings: Any,
    ocr_confidences: list[float],
) -> list[dict[str, Any]]:
    use_ocr_a = _needs_ocr(words_a, settings)
    use_ocr_b = _needs_ocr(words_b, settings)

    if (use_ocr_a or use_ocr_b) and settings.ocr_enabled:
        final_a = words_a
        final_b = words_b
        if use_ocr_a:
            final_a, confidence_a = extract_ocr_words(
                page_image_a.convert("RGB"),
                confidence_threshold=settings.ocr_confidence_threshold,
                adapter=settings.ocr_adapter,
                language=settings.ocr_language,
                enabled=True,
            )
            if confidence_a > 0:
                ocr_confidences.append(confidence_a)
        if use_ocr_b:
            final_b, confidence_b = extract_ocr_words(
                aligned_b.convert("RGB"),
                confidence_threshold=settings.ocr_confidence_threshold,
                adapter=settings.ocr_adapter,
                language=settings.ocr_language,
                enabled=True,
            )
            if confidence_b > 0:
                ocr_confidences.append(confidence_b)
        if final_a or final_b:
            return word_diff_page(final_a, final_b, page)
        return []

    if words_a or words_b:
        return word_diff_page(words_a, words_b, page)
    return []


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
        return {"type": "docx", "supports_overlays": True, "primary_axis": "page"}
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
