from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

JobStatus = Literal["queued", "running", "completed", "failed", "cancelled"]
ChangeType = Literal["added", "removed", "modified", "warning"]
ChangeCategory = Literal[
    "text",
    "visual",
    "file",
    "metadata",
    "formatting",
    "table",
    "image",
    "structure",
]
Severity = Literal["low", "medium", "high"]


class ErrorInfo(BaseModel):
    code: str
    message: str


class CompareResponse(BaseModel):
    job_id: str
    status: JobStatus
    request_id: str | None = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    file_a: str
    file_b: str
    file_a_type: str
    file_b_type: str
    created_at: str
    updated_at: str
    started_at: str | None = None
    completed_at: str | None = None
    error: ErrorInfo | None = None


class BoundingBox(BaseModel):
    page: int
    x: float
    y: float
    width: float
    height: float


class SourceRef(BaseModel):
    document: Literal["a", "b", "both"]
    page: int | None = None
    part: str | None = None
    block_id: str | None = None
    paragraph: int | None = None
    run: int | None = None
    table: int | None = None
    row: int | None = None
    column: int | None = None
    image: int | None = None


class ChangeItem(BaseModel):
    id: str
    type: ChangeType
    category: ChangeCategory
    severity: Severity
    confidence: float
    message: str
    source_ref: SourceRef
    bbox: BoundingBox | None = None


class JobResult(BaseModel):
    result_schema_version: str
    summary: str
    file_type: str
    changes: list[ChangeItem]
    diagnostics: dict[str, Any] | None = None
