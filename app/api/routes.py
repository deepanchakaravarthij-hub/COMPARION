from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.schemas.jobs import CompareResponse, JobResult, JobStatusResponse
from app.services.compare_service import compare_files
from app.services.job_store import create_job, get_job, set_job_result, set_job_status

router = APIRouter()


@router.post("/compare", response_model=CompareResponse)
async def compare(
    background_tasks: BackgroundTasks,
    file_a: Annotated[UploadFile, File()],
    file_b: Annotated[UploadFile, File()],
) -> CompareResponse:
    if not file_a.filename or not file_b.filename:
        raise HTTPException(status_code=400, detail="Both files must include a filename")

    job_id = create_job(file_a.filename, file_b.filename)
    content_a = await file_a.read()
    content_b = await file_b.read()

    background_tasks.add_task(
        _run_compare_job, job_id, file_a.filename, file_b.filename, content_a, content_b
    )
    return CompareResponse(job_id=job_id, status="queued")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def job_status(job_id: str) -> JobStatusResponse:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(
        job_id=job_id, status=job["status"], file_a=job["file_a"], file_b=job["file_b"]
    )


@router.get("/jobs/{job_id}/result", response_model=JobResult)
def job_result(job_id: str) -> JobResult:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] != "completed":
        raise HTTPException(status_code=409, detail="Job not completed")
    return JobResult(**job["result"])


def _run_compare_job(
    job_id: str, file_a_name: str, file_b_name: str, content_a: bytes, content_b: bytes
) -> None:
    set_job_status(job_id, "running")
    result = compare_files(file_a_name, file_b_name, content_a, content_b)
    set_job_result(job_id, result)
