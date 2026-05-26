from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from app.schemas.jobs import CompareResponse, ErrorInfo, JobResult, JobStatusResponse
from app.services.compare_service import compare_files
from app.services.job_store import (
    create_job,
    get_job,
    set_job_failed,
    set_job_files,
    set_job_result,
    set_job_status,
)
from app.services.report_service import build_html_report
from app.services.storage import storage
from app.services.upload_validation import validate_upload

router = APIRouter()


@router.post("/compare", response_model=CompareResponse)
async def compare(
    request: Request,
    background_tasks: BackgroundTasks,
    file_a: Annotated[UploadFile, File()],
    file_b: Annotated[UploadFile, File()],
) -> CompareResponse:
    validated_a = await validate_upload(file_a)
    validated_b = await validate_upload(file_b)

    if validated_a.file_type != validated_b.file_type:
        raise HTTPException(status_code=400, detail="Both files must have the same supported type")

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

    background_tasks.add_task(
        _run_compare_job,
        job_id,
        validated_a.filename,
        validated_b.filename,
        validated_a.content,
        validated_b.content,
    )
    return CompareResponse(
        job_id=job_id,
        status="queued",
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def job_status(job_id: str) -> JobStatusResponse:
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


@router.get("/jobs/{job_id}/result", response_model=JobResult)
def job_result(job_id: str) -> JobResult:
    job = _get_existing_job(job_id)
    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="Job not completed")
    return JobResult(**job["result"])


@router.get("/jobs/{job_id}/report.html", response_class=HTMLResponse)
def job_report(job_id: str) -> HTMLResponse:
    job = _get_existing_job(job_id)
    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="Job not completed")
    if not job["report_path"]:
        raise HTTPException(status_code=404, detail="Report not found")
    return HTMLResponse(storage.read_text(job["report_path"]))


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
    last_error: Exception | None = None
    for _attempt in range(2):
        try:
            result = compare_files(file_a_name, file_b_name, content_a, content_b)
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
            return
        except (ValidationError, ValueError) as exc:
            set_job_failed(job_id, "comparison_error", str(exc))
            return
        except Exception as exc:
            last_error = exc

    if last_error is not None:
        set_job_failed(job_id, "internal_error", str(last_error))
