from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class UdmBoundingBox(BaseModel):
    page: int | None = None
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None


class UdmBlock(BaseModel):
    block_id: str
    type: Literal["text", "table", "image", "shape", "metadata", "structure", "unknown"]
    category: str
    change_type: str
    severity: str
    confidence: float
    text: str | None = None
    source_ref: dict[str, Any]
    bbox: UdmBoundingBox | None = None


class UdmDocument(BaseModel):
    doc_id: str
    version_id: str
    format: str
    blocks: list[UdmBlock]


class UdmPayload(BaseModel):
    schema_version: str
    documents: list[UdmDocument]
