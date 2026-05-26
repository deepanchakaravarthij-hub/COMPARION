from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

JobRecord = dict[str, Any]

_jobs: dict[str, JobRecord] = {}
_lock = Lock()


def create_job(file_a: str, file_b: str) -> str:
    job_id = str(uuid4())
    with _lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "file_a": file_a,
            "file_b": file_b,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "result": None,
        }
    return job_id


def get_job(job_id: str) -> JobRecord | None:
    return _jobs.get(job_id)


def set_job_status(job_id: str, status: str) -> None:
    with _lock:
        if job_id in _jobs:
            _jobs[job_id]["status"] = status


def set_job_result(job_id: str, result: dict[str, Any]) -> None:
    with _lock:
        if job_id in _jobs:
            _jobs[job_id]["result"] = result
            _jobs[job_id]["status"] = "completed"
