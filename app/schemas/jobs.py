from pydantic import BaseModel


class CompareResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    file_a: str
    file_b: str


class ChangeItem(BaseModel):
    type: str
    message: str


class JobResult(BaseModel):
    summary: str
    file_type: str
    changes: list[ChangeItem]
