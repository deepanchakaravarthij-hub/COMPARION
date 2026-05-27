from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from io import BytesIO
from typing import Annotated, Any
from urllib.parse import quote, urlencode

import fitz  # type: ignore[import-untyped]
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, Response
from PIL import Image
from pydantic import ValidationError

from app.core.config import get_settings
from app.schemas.jobs import (
    CompareResponse,
    ErrorInfo,
    JobHistoryItem,
    JobHistoryResponse,
    JobResult,
    JobStatusResponse,
)
from app.services.compare_service import compare_files
from app.services.job_store import (
    add_audit_event,
    add_dead_letter_job,
    cleanup_expired_jobs,
    create_job,
    get_job,
    get_or_create_idempotent_job,
    list_jobs,
    set_job_failed,
    set_job_files,
    set_job_result,
    set_job_status,
    summarize_job_statuses,
)
from app.services.report_service import build_html_report
from app.services.storage import storage
from app.services.task_queue import enqueue_compare_job
from app.services.upload_validation import validate_upload

router = APIRouter()
SUPPORTED_RESULT_VERSIONS = {"2.0", "2.1"}
logger = logging.getLogger("comparion.api")
ARTIFACT_LABELS = {"a": "file_a_path", "b": "file_b_path"}


@router.post("/compare", response_model=CompareResponse)
async def compare(
    request: Request,
    background_tasks: BackgroundTasks,
    file_a: Annotated[UploadFile, File()],
    file_b: Annotated[UploadFile, File()],
    idempotency_key: str | None = Query(default=None, alias="idempotency_key"),
) -> CompareResponse:
    _require_auth(request)
    validated_a = await validate_upload(file_a)
    validated_b = await validate_upload(file_b)

    if validated_a.file_type != validated_b.file_type:
        raise HTTPException(status_code=400, detail="Both files must have the same supported type")

    request_id = getattr(request.state, "request_id", None)
    request_hash = _request_hash(validated_a, validated_b)

    if idempotency_key:
        def _create_job() -> str:
            return create_job(
                validated_a.filename,
                validated_b.filename,
                validated_a.file_type,
                validated_b.file_type,
                validated_a.sha256,
                validated_b.sha256,
            )

        job_id, reused = get_or_create_idempotent_job(idempotency_key, request_hash, _create_job)
        if reused:
            add_audit_event(
                event_type="job_idempotency_reused",
                job_id=job_id,
                request_id=request_id,
                details={"idempotency_key": idempotency_key},
            )
            job = _get_existing_job(job_id)
            return CompareResponse(
                job_id=job_id,
                status=job["status"],
                request_id=request_id,
            )
    else:
        job_id = create_job(
            validated_a.filename,
            validated_b.filename,
            validated_a.file_type,
            validated_b.file_type,
            validated_a.sha256,
            validated_b.sha256,
        )

    file_a_path = storage.save_upload(job_id, "a", validated_a.filename, validated_a.content)
    file_b_path = storage.save_upload(job_id, "b", validated_b.filename, validated_b.content)
    set_job_files(job_id, file_a_path, file_b_path)

    queue_info = enqueue_compare_job(
        background_tasks,
        _run_compare_job,
        job_id,
        validated_a.filename,
        validated_b.filename,
        validated_a.content,
        validated_b.content,
    )
    add_audit_event(
        event_type="job_submitted",
        job_id=job_id,
        request_id=request_id,
        details={
            "file_type": validated_a.file_type,
            "queue_mode": queue_info["mode"],
            "idempotency_key": idempotency_key,
        },
    )
    return CompareResponse(
        job_id=job_id,
        status="queued",
        request_id=request_id,
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def job_status(request: Request, job_id: str) -> JobStatusResponse:
    _require_auth(request)
    job = _get_existing_job(job_id)
    error = None
    if job["error_code"] and job["error_message"]:
        error = ErrorInfo(code=job["error_code"], message=job["error_message"])

    return JobStatusResponse(
        job_id=job_id,
        status=job["status"],
        file_a=job["file_a"],
        file_b=job["file_b"],
        file_a_type=job["file_a_type"],
        file_b_type=job["file_b_type"],
        created_at=job["created_at"],
        updated_at=job["updated_at"],
        started_at=job["started_at"],
        completed_at=job["completed_at"],
        error=error,
    )


@router.get("/jobs", response_model=JobHistoryResponse)
def jobs(
    request: Request,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None),
) -> JobHistoryResponse:
    _require_auth(request)
    items, total = list_jobs(limit=limit, offset=offset, status=status)
    return JobHistoryResponse(items=[JobHistoryItem(**item) for item in items], total=total)


@router.get("/jobs/{job_id}/result", response_model=JobResult, response_model_exclude_none=True)
def job_result(
    request: Request,
    job_id: str,
    result_schema_version: str = Query(default="2.1"),
    limit: int | None = Query(default=None, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    category: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    change_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
) -> JobResult:
    _require_auth(request)
    job = _get_existing_job(job_id)
    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="Job not completed")
    if result_schema_version not in SUPPORTED_RESULT_VERSIONS:
        raise HTTPException(status_code=400, detail="Unsupported result schema version")

    result = _filter_and_paginate_result(
        job["result"],
        limit=limit,
        offset=offset,
        category=category,
        severity=severity,
        change_type=change_type,
        search=search,
    )
    rendered = _render_result_version(result, result_schema_version)
    return JobResult(**rendered)


@router.get("/jobs/{job_id}/report.html", response_class=HTMLResponse)
def job_report(
    request: Request,
    job_id: str,
    token: str | None = Query(default=None),
    expires: int | None = Query(default=None),
) -> HTMLResponse:
    _require_auth(request)
    job = _get_existing_job(job_id)
    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="Job not completed")
    if not job["report_path"]:
        raise HTTPException(status_code=404, detail="Report not found")
    settings = get_settings()
    if settings.object_storage_enabled:
        if not token or not expires:
            raise HTTPException(status_code=403, detail="Signed report token is required")
        if not _is_valid_report_token(job_id=job_id, token=token, expires=expires):
            raise HTTPException(status_code=403, detail="Invalid or expired report token")
    add_audit_event(
        event_type="report_accessed",
        job_id=job_id,
        request_id=getattr(request.state, "request_id", None),
        details={"signed": settings.object_storage_enabled},
    )
    return HTMLResponse(storage.read_text(job["report_path"]))


@router.get("/jobs/{job_id}/report-link")
def job_report_link(request: Request, job_id: str) -> dict[str, Any]:
    _require_auth(request)
    job = _get_existing_job(job_id)
    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="Job not completed")
    if not job["report_path"]:
        raise HTTPException(status_code=404, detail="Report not found")
    settings = get_settings()
    if not settings.object_storage_enabled:
        add_audit_event(
            event_type="report_link_generated",
            job_id=job_id,
            request_id=getattr(request.state, "request_id", None),
            details={"signed": False},
        )
        return {"url": f"/v1/jobs/{job_id}/report.html", "signed": False}

    expires = int(time.time()) + settings.signed_url_ttl_seconds
    token = _sign_report_token(job_id=job_id, expires=expires)
    query = urlencode({"token": token, "expires": expires})
    payload = {
        "url": f"/v1/jobs/{job_id}/report.html?{query}",
        "signed": True,
        "expires": expires,
    }
    add_audit_event(
        event_type="report_link_generated",
        job_id=job_id,
        request_id=getattr(request.state, "request_id", None),
        details={"signed": True, "expires": expires},
    )
    return payload


@router.get("/jobs/{job_id}/comparison.pdf")
def job_comparison_pdf(request: Request, job_id: str) -> Response:
    _require_auth(request)
    job = _get_existing_job(job_id)
    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="Job not completed")
    if job["file_a_type"] != "pdf" or job["file_b_type"] != "pdf":
        raise HTTPException(status_code=415, detail="Comparison PDF export is available for PDFs")

    file_a_path = _get_artifact_path(job, "a")
    file_b_path = _get_artifact_path(job, "b")
    pdf_bytes = _build_draftable_pdf_export(
        left_name=str(job["file_a"]),
        right_name=str(job["file_b"]),
        left_content=storage.read_bytes(file_a_path),
        right_content=storage.read_bytes(file_b_path),
    )
    filename = f'{job["file_a"]} \u2192 {job["file_b"]} - Draftable.pdf'
    add_audit_event(
        event_type="comparison_pdf_exported",
        job_id=job_id,
        request_id=getattr(request.state, "request_id", None),
        details={"filename": filename},
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                "attachment; "
                'filename="comparison.pdf"; '
                f"filename*=UTF-8''{quote(filename)}"
            )
        },
    )


@router.get("/jobs/{job_id}/artifact/{label}")
def job_artifact(
    request: Request,
    job_id: str,
    label: str,
    token: str | None = Query(default=None),
    expires: int | None = Query(default=None),
) -> FileResponse:
    _require_auth(request)
    job = _get_existing_job(job_id)
    artifact_path = _get_artifact_path(job, label)
    settings = get_settings()
    if settings.object_storage_enabled:
        if not token or not expires:
            raise HTTPException(status_code=403, detail="Signed artifact token is required")
        if not _is_valid_artifact_token(
            job_id=job_id,
            label=label,
            token=token,
            expires=expires,
        ):
            raise HTTPException(status_code=403, detail="Invalid or expired artifact token")
    add_audit_event(
        event_type="artifact_accessed",
        job_id=job_id,
        request_id=getattr(request.state, "request_id", None),
        details={"label": label, "signed": settings.object_storage_enabled},
    )
    filename = job["file_a"] if label == "a" else job["file_b"]
    return FileResponse(
        artifact_path,
        filename=filename,
        media_type=_artifact_media_type(job["file_a_type"]),
    )


@router.get("/jobs/{job_id}/artifact-link/{label}")
def job_artifact_link(request: Request, job_id: str, label: str) -> dict[str, Any]:
    _require_auth(request)
    job = _get_existing_job(job_id)
    artifact_path_key = ARTIFACT_LABELS.get(label)
    if artifact_path_key is None or not job.get(artifact_path_key):
        raise HTTPException(status_code=404, detail="Artifact not found")
    settings = get_settings()
    if not settings.object_storage_enabled:
        return {
            "url": f"/v1/jobs/{job_id}/artifact/{label}",
            "signed": False,
            "label": label,
        }

    expires = int(time.time()) + settings.signed_url_ttl_seconds
    token = _sign_artifact_token(job_id=job_id, label=label, expires=expires)
    query = urlencode({"token": token, "expires": expires})
    return {
        "url": f"/v1/jobs/{job_id}/artifact/{label}?{query}",
        "signed": True,
        "label": label,
        "expires": expires,
    }


@router.get("/jobs/{job_id}/preview/{label}/manifest")
def job_preview_manifest(request: Request, job_id: str, label: str) -> dict[str, Any]:
    _require_auth(request)
    job = _get_existing_job(job_id)
    artifact_path = _get_artifact_path(job, label)
    file_type = str(job["file_a_type"])
    if file_type == "pdf":
        page_count = _pdf_page_count(storage.read_bytes(artifact_path))
    elif file_type == "image":
        page_count = 1
    elif file_type == "pptx":
        from app.services.comparison.pptx_render import pptx_slide_count

        page_count = pptx_slide_count(storage.read_bytes(artifact_path))
    elif file_type == "docx":
        from app.services.comparison.docx_render import estimate_page_count

        page_count = estimate_page_count(storage.read_bytes(artifact_path))
    else:
        raise HTTPException(
            status_code=415,
            detail="Preview manifest is available for PDF, image, PPTX, and DOCX",
        )
    return {"label": label, "file_type": file_type, "page_count": page_count}


@router.get("/jobs/{job_id}/preview/{label}/page/{page}")
def job_preview_page(request: Request, job_id: str, label: str, page: int) -> Response:
    _require_auth(request)
    if page < 1:
        raise HTTPException(status_code=400, detail="Page numbers are 1-based")
    job = _get_existing_job(job_id)
    artifact_path = _get_artifact_path(job, label)
    content = storage.read_bytes(artifact_path)
    file_type = str(job["file_a_type"])
    if file_type == "pdf":
        image_bytes = _render_pdf_page(content, page)
    elif file_type == "image" and page == 1:
        image_bytes = _normalize_image_preview(content)
    elif file_type == "pptx":
        from app.services.comparison.pptx_render import render_pptx_slide_png

        try:
            image_bytes = render_pptx_slide_png(content, page)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    elif file_type == "docx":
        from app.services.comparison.docx_render import render_docx_page_png

        try:
            image_bytes = render_docx_page_png(content, page)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    else:
        raise HTTPException(
            status_code=415,
            detail="Preview page is available for PDF, image, PPTX, and DOCX",
        )
    add_audit_event(
        event_type="preview_accessed",
        job_id=job_id,
        request_id=getattr(request.state, "request_id", None),
        details={"label": label, "page": page},
    )
    return Response(content=image_bytes, media_type="image/png")


@router.get("/metrics")
def metrics(request: Request) -> dict[str, Any]:
    _require_auth(request)
    statuses = summarize_job_statuses()
    total = sum(statuses.values())
    failed = statuses.get("failed", 0)
    queued_and_running = statuses.get("queued", 0) + statuses.get("running", 0)
    failure_rate = (failed / total) if total else 0.0
    settings = get_settings()
    alerts = []
    if failure_rate > settings.metrics_alert_failure_rate_threshold:
        alerts.append(
            {
                "type": "failure_rate",
                "threshold": settings.metrics_alert_failure_rate_threshold,
                "observed": round(failure_rate, 4),
            }
        )
    if queued_and_running > settings.metrics_alert_queue_depth_threshold:
        alerts.append(
            {
                "type": "queue_depth",
                "threshold": settings.metrics_alert_queue_depth_threshold,
                "observed": queued_and_running,
            }
        )
    return {
        "job_status_counts": statuses,
        "queue_depth": queued_and_running,
        "failure_rate": round(failure_rate, 4),
        "alerts": alerts,
    }


@router.post("/ops/retention/cleanup")
def retention_cleanup(request: Request) -> dict[str, Any]:
    _require_auth(request)
    settings = get_settings()
    cleanup_info = cleanup_expired_jobs(settings.retention_days)
    storage_deleted = _cleanup_storage_directories(settings.retention_days)
    add_audit_event(
        event_type="retention_cleanup",
        request_id=getattr(request.state, "request_id", None),
        details={
            "retention_days": settings.retention_days,
            "db_deleted": cleanup_info["deleted_jobs"],
            "storage_deleted": storage_deleted,
        },
    )
    return {
        **cleanup_info,
        "storage_deleted": storage_deleted,
        "retention_days": settings.retention_days,
    }


def _get_existing_job(job_id: str) -> dict[str, Any]:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _run_compare_job(
    job_id: str,
    file_a_name: str,
    file_b_name: str,
    content_a: bytes,
    content_b: bytes,
) -> None:
    set_job_status(job_id, "running")
    add_audit_event(event_type="job_started", job_id=job_id)
    last_error: Exception | None = None
    settings = get_settings()
    for attempt in range(settings.max_retry_attempts):
        try:
            result = compare_files(file_a_name, file_b_name, content_a, content_b, job_id=job_id)
            JobResult(**result)
            result_path = storage.save_text(
                job_id,
                "result.json",
                json.dumps(result, indent=2, sort_keys=True),
            )
            job = get_job(job_id)
            if job is None:
                raise RuntimeError("Job disappeared during processing")
            report = build_html_report(job, result)
            report_path = storage.save_text(job_id, "report.html", report)
            set_job_result(job_id, result, result_path, report_path)
            add_audit_event(
                event_type="job_completed",
                job_id=job_id,
                details={"attempt": attempt + 1},
            )
            return
        except (ValidationError, ValueError) as exc:
            set_job_failed(job_id, "comparison_error", str(exc))
            add_dead_letter_job(
                job_id=job_id,
                reason="comparison_error",
                payload={"message": str(exc), "attempt": attempt + 1},
            )
            add_audit_event(
                event_type="job_failed",
                job_id=job_id,
                details={"code": "comparison_error", "attempt": attempt + 1},
            )
            return
        except Exception as exc:
            last_error = exc
            if attempt < settings.max_retry_attempts - 1:
                time.sleep(settings.retry_backoff_ms / 1000)

    if last_error is not None:
        set_job_failed(job_id, "internal_error", str(last_error))
        add_dead_letter_job(
            job_id=job_id,
            reason="internal_error",
            payload={"message": str(last_error), "max_attempts": settings.max_retry_attempts},
        )
        add_audit_event(
            event_type="job_failed",
            job_id=job_id,
            details={"code": "internal_error", "max_attempts": settings.max_retry_attempts},
        )


def _filter_and_paginate_result(
    result: dict[str, Any],
    *,
    limit: int | None,
    offset: int,
    category: str | None,
    severity: str | None,
    change_type: str | None,
    search: str | None,
) -> dict[str, Any]:
    changes = result.get("changes", [])
    filtered = []
    needle = search.lower() if search else None
    for change in changes:
        if category and change.get("category") != category:
            continue
        if severity and change.get("severity") != severity:
            continue
        if change_type and change.get("type") != change_type:
            continue
        if needle and needle not in str(change.get("message", "")).lower():
            continue
        filtered.append(change)

    start = offset
    end = offset + limit if limit is not None else None
    paged = filtered[start:end]
    has_more = end is not None and end < len(filtered)
    return {
        **result,
        "changes": paged,
        "pagination": {
            "offset": offset,
            "limit": limit,
            "total_filtered": len(filtered),
            "total_changes": len(changes),
            "has_more": has_more,
        },
    }


def _render_result_version(result: dict[str, Any], version: str) -> dict[str, Any]:
    if version == "2.1":
        return {**result, "result_schema_version": "2.1"}

    mapped = []
    for change in result.get("changes", []):
        item = dict(change)
        if item.get("category") in {"formula"}:
            item["category"] = "text"
        elif item.get("category") in {"sheet", "slide"}:
            item["category"] = "structure"
        source_ref = dict(item.get("source_ref", {}))
        source_ref.pop("sheet", None)
        source_ref.pop("cell", None)
        source_ref.pop("slide", None)
        item["source_ref"] = source_ref
        item.pop("semantic_label", None)
        item.pop("semantic_score", None)
        mapped.append(item)
    rendered = {**result, "changes": mapped, "result_schema_version": "2.0"}
    rendered.pop("udm", None)
    rendered.pop("semantic", None)
    rendered.pop("viewer_hints", None)
    return rendered


def _sign_report_token(job_id: str, expires: int) -> str:
    message = f"{job_id}:{expires}".encode()
    secret = get_settings().signed_url_secret.encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def _sign_artifact_token(job_id: str, label: str, expires: int) -> str:
    message = f"{job_id}:{label}:{expires}".encode()
    secret = get_settings().signed_url_secret.encode()
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def _is_valid_report_token(job_id: str, token: str, expires: int) -> bool:
    if expires < int(time.time()):
        return False
    expected = _sign_report_token(job_id=job_id, expires=expires)
    return hmac.compare_digest(expected, token)


def _is_valid_artifact_token(job_id: str, label: str, token: str, expires: int) -> bool:
    if expires < int(time.time()):
        return False
    expected = _sign_artifact_token(job_id=job_id, label=label, expires=expires)
    return hmac.compare_digest(expected, token)


def _artifact_media_type(file_type: str) -> str:
    return {
        "pdf": "application/pdf",
        "image": "image/png",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }.get(file_type, "application/octet-stream")


def _get_artifact_path(job: dict[str, Any], label: str) -> str:
    artifact_path_key = ARTIFACT_LABELS.get(label)
    if artifact_path_key is None:
        raise HTTPException(status_code=404, detail="Artifact label not found")
    artifact_path = job.get(artifact_path_key)
    if not artifact_path:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return str(artifact_path)


def _pdf_page_count(content: bytes) -> int:
    with fitz.open(stream=content, filetype="pdf") as document:
        return int(document.page_count)


def _render_pdf_page(content: bytes, page: int) -> bytes:
    with fitz.open(stream=content, filetype="pdf") as document:
        if page > document.page_count:
            raise HTTPException(status_code=404, detail="Page not found")
        pdf_page = document.load_page(page - 1)
        pixmap = pdf_page.get_pixmap(matrix=fitz.Matrix(1.75, 1.75), alpha=False)
        return bytes(pixmap.tobytes("png"))


def _normalize_image_preview(content: bytes) -> bytes:
    with Image.open(BytesIO(content)) as image:
        output = BytesIO()
        image.convert("RGB").save(output, format="PNG")
        return output.getvalue()


def _build_draftable_pdf_export(
    *,
    left_name: str,
    right_name: str,
    left_content: bytes,
    right_content: bytes,
) -> bytes:
    output = fitz.open()
    _add_draftable_cover(output, left_name=left_name, right_name=right_name)
    with (
        fitz.open(stream=left_content, filetype="pdf") as left_document,
        fitz.open(stream=right_content, filetype="pdf") as right_document,
    ):
        max_pages = max(left_document.page_count, right_document.page_count)
        for page_index in range(max_pages):
            if page_index < left_document.page_count:
                output.insert_pdf(left_document, from_page=page_index, to_page=page_index)
            else:
                _add_blank_page(output, right_document, page_index)

            if page_index < right_document.page_count:
                output.insert_pdf(right_document, from_page=page_index, to_page=page_index)
            else:
                _add_blank_page(output, left_document, page_index)

    for index, page in enumerate(output, start=1):
        if index == 1:
            continue
        page.insert_textbox(
            fitz.Rect(0, page.rect.height - 28, page.rect.width, page.rect.height - 8),
            f"-- {index - 1} of {len(output) - 1} --",
            align=fitz.TEXT_ALIGN_CENTER,
            fontsize=9,
            color=(0.35, 0.35, 0.35),
        )
    return bytes(output.tobytes(deflate=True))


def _add_draftable_cover(output: fitz.Document, *, left_name: str, right_name: str) -> None:
    page = output.new_page(width=595, height=842)
    body = (
        "Draftable Comparison Export\n\n"
        "This document is an exported comparison generated by COMPARION in a "
        "Draftable-style layout.\n\n"
        f"Left document:\t{left_name}\n"
        f"Right document:\t{right_name}\n\n"
        "What is this document?\n"
        "This is a comparison of two documents. The two documents are interleaved "
        "such that the left document is displayed on even pages and the right "
        "document is displayed on odd pages after this cover page.\n\n"
        "Is there a specific way I should view this file?\n"
        "This document is intended to be viewed in Two Page Continuous mode. "
        "Blank pages are inserted when one document has fewer pages so that both "
        "documents remain aligned as much as possible.\n\n"
        "How do I read the changes?\n"
        "Use the COMPARION web viewer for the interactive change list, semantic "
        "labels, and synchronized navigation."
    )
    page.insert_textbox(
        fitz.Rect(54, 54, 540, 790),
        body,
        fontsize=11,
        lineheight=1.25,
        fontname="helv",
    )


def _add_blank_page(output: fitz.Document, reference: fitz.Document, page_index: int) -> None:
    if reference.page_count:
        source_page = reference.load_page(min(page_index, reference.page_count - 1))
        rect = source_page.rect
        page = output.new_page(width=rect.width, height=rect.height)
    else:
        page = output.new_page(width=595, height=842)
    page.insert_textbox(
        fitz.Rect(0, page.rect.height / 2 - 12, page.rect.width, page.rect.height / 2 + 12),
        "Blank page inserted to preserve alignment",
        align=fitz.TEXT_ALIGN_CENTER,
        fontsize=10,
        color=(0.55, 0.55, 0.55),
    )


def _request_hash(upload_a: Any, upload_b: Any) -> str:
    payload = "|".join(
        [
            upload_a.filename,
            upload_b.filename,
            upload_a.file_type,
            upload_b.file_type,
            upload_a.sha256,
            upload_b.sha256,
        ]
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _require_auth(request: Request) -> None:
    settings = get_settings()
    if not settings.auth_required:
        return

    supplied_api_key = request.headers.get("X-API-Key", "")
    if settings.auth_api_key and hmac.compare_digest(supplied_api_key, settings.auth_api_key):
        return

    authorization = request.headers.get("Authorization", "")
    if settings.auth_bearer_token and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        if hmac.compare_digest(token, settings.auth_bearer_token):
            return

    raise HTTPException(status_code=401, detail="Authentication required")


def _cleanup_storage_directories(retention_days: int) -> int:
    jobs_root = storage.root / "jobs"
    if not jobs_root.exists():
        return 0
    cutoff = time.time() - retention_days * 86400
    removed = 0
    for entry in jobs_root.iterdir():
        if not entry.is_dir():
            continue
        if entry.stat().st_mtime > cutoff:
            continue
        for child in entry.iterdir():
            if child.is_file():
                child.unlink(missing_ok=True)
        try:
            entry.rmdir()
            removed += 1
        except OSError:
            logger.warning("retention_skip_non_empty_dir path=%s", entry)
    return removed
