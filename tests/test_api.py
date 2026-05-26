from __future__ import annotations

from io import BytesIO

import fitz
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.main import app
from app.services.compare_service import compare_files

client = TestClient(app)


def _image_bytes(color: str = "white", mark: bool = False) -> bytes:
    image = Image.new("RGB", (100, 100), color)
    if mark:
        draw = ImageDraw.Draw(image)
        draw.rectangle((20, 20, 50, 50), fill="black")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _pdf_bytes(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    content = document.tobytes()
    document.close()
    return content


def test_health() -> None:
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert res.json()["environment"] == "local"
    assert "X-Request-ID" in res.headers


def test_request_id_is_preserved() -> None:
    res = client.get("/health", headers={"X-Request-ID": "test-request-id"})
    assert res.status_code == 200
    assert res.headers["X-Request-ID"] == "test-request-id"


def test_compare_pdf_and_fetch_result_and_report() -> None:
    files = {
        "file_a": ("a.pdf", _pdf_bytes("hello contract"), "application/pdf"),
        "file_b": ("b.pdf", _pdf_bytes("hello updated contract"), "application/pdf"),
    }
    compare_res = client.post("/v1/compare", files=files)
    assert compare_res.status_code == 200
    assert compare_res.json()["request_id"]

    job_id = compare_res.json()["job_id"]
    status_res = client.get(f"/v1/jobs/{job_id}")
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "completed"
    assert status_res.json()["file_a_type"] == "pdf"

    result_res = client.get(f"/v1/jobs/{job_id}/result")
    assert result_res.status_code == 200
    payload = result_res.json()
    assert payload["result_schema_version"] == "2.0"
    assert payload["file_type"] == "pdf"
    assert payload["changes"]

    report_res = client.get(f"/v1/jobs/{job_id}/report.html")
    assert report_res.status_code == 200
    assert "COMPARION Report" in report_res.text


def test_compare_identical_images_has_no_changes() -> None:
    content = _image_bytes()
    files = {
        "file_a": ("a.png", content, "image/png"),
        "file_b": ("b.png", content, "image/png"),
    }
    compare_res = client.post("/v1/compare", files=files)
    assert compare_res.status_code == 200

    job_id = compare_res.json()["job_id"]
    result_res = client.get(f"/v1/jobs/{job_id}/result")
    assert result_res.status_code == 200
    payload = result_res.json()
    assert payload["file_type"] == "image"
    assert payload["changes"] == []
    assert payload["summary"] == "No differences detected"


def test_rejects_unsupported_extension() -> None:
    files = {
        "file_a": ("a.txt", b"hello", "text/plain"),
        "file_b": ("b.txt", b"hello", "text/plain"),
    }
    res = client.post("/v1/compare", files=files)
    assert res.status_code == 415


def test_rejects_mismatched_supported_types() -> None:
    files = {
        "file_a": ("a.pdf", _pdf_bytes("hello"), "application/pdf"),
        "file_b": ("b.png", _image_bytes(), "image/png"),
    }
    res = client.post("/v1/compare", files=files)
    assert res.status_code == 400


def test_failed_job_includes_error_reason() -> None:
    files = {
        "file_a": ("a.pdf", b"not a pdf", "application/pdf"),
        "file_b": ("b.pdf", b"also not a pdf", "application/pdf"),
    }
    compare_res = client.post("/v1/compare", files=files)
    assert compare_res.status_code == 200

    job_id = compare_res.json()["job_id"]
    status_res = client.get(f"/v1/jobs/{job_id}")
    assert status_res.status_code == 200
    payload = status_res.json()
    assert payload["status"] == "failed"
    assert payload["error"]["code"] == "internal_error"
    assert payload["error"]["message"]

    result_res = client.get(f"/v1/jobs/{job_id}/result")
    assert result_res.status_code == 409


def test_image_diff_is_deterministic() -> None:
    result_a = compare_files("a.png", "b.png", _image_bytes(), _image_bytes(mark=True))
    result_b = compare_files("a.png", "b.png", _image_bytes(), _image_bytes(mark=True))
    assert result_a["changes"] == result_b["changes"]
    assert result_a["changes"][0]["bbox"] == {
        "page": 1,
        "x": 0.61,
        "y": 0.5,
        "width": 0.32,
        "height": 0.32,
    }
