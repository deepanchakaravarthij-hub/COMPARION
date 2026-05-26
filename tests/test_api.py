from __future__ import annotations

from io import BytesIO

import fitz  # type: ignore[import-untyped]
from docx import Document
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
    content = bytes(document.tobytes())
    document.close()
    return content


def _docx_bytes(
    paragraph_runs: list[list[tuple[str, bool]]],
    table_rows: list[list[str]] | None = None,
) -> bytes:
    document = Document()
    for runs in paragraph_runs:
        paragraph = document.add_paragraph()
        for text, bold in runs:
            run = paragraph.add_run(text)
            run.bold = bold

    if table_rows:
        table = document.add_table(rows=len(table_rows), cols=len(table_rows[0]))
        for row_index, row in enumerate(table_rows):
            for column_index, value in enumerate(row):
                table.cell(row_index, column_index).text = value

    output = BytesIO()
    document.save(output)
    return output.getvalue()


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


def test_compare_docx_and_fetch_result_and_report() -> None:
    file_a = _docx_bytes(
        [
            [("Agreement summary", False)],
            [("Payment due in 30 days", False)],
            [("Reviewed by Legal", False)],
        ],
        [["Clause", "Value"], ["Fee", "100"]],
    )
    file_b = _docx_bytes(
        [
            [("Agreement summary", False)],
            [("Payment due in 45 days", False)],
            [("Reviewed by Legal", True)],
        ],
        [["Clause", "Value"], ["Fee", "125"]],
    )
    files = {
        "file_a": (
            "a.docx",
            file_a,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        "file_b": (
            "b.docx",
            file_b,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    }

    compare_res = client.post("/v1/compare", files=files)
    assert compare_res.status_code == 200

    job_id = compare_res.json()["job_id"]
    status_res = client.get(f"/v1/jobs/{job_id}")
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "completed"
    assert status_res.json()["file_a_type"] == "docx"

    result_res = client.get(f"/v1/jobs/{job_id}/result")
    assert result_res.status_code == 200
    payload = result_res.json()
    categories = {change["category"] for change in payload["changes"]}
    assert {"text", "formatting", "table"}.issubset(categories)
    assert payload["diagnostics"]["docx"]["paragraph_count"]["a"] >= 3

    report_res = client.get(f"/v1/jobs/{job_id}/report.html")
    assert report_res.status_code == 200
    assert "Text changes" in report_res.text
    assert "Formatting changes" in report_res.text
    assert "Table changes" in report_res.text


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


def test_docx_diff_is_deterministic() -> None:
    file_a = _docx_bytes(
        [[("Alpha", False)], [("Beta", False)]],
        [["Key", "Value"], ["Limit", "10"]],
    )
    file_b = _docx_bytes(
        [[("Beta", False)], [("Alpha changed", False)]],
        [["Key", "Value"], ["Limit", "20"]],
    )
    result_a = compare_files("a.docx", "b.docx", file_a, file_b)
    result_b = compare_files("a.docx", "b.docx", file_a, file_b)
    assert result_a["changes"] == result_b["changes"]
    assert {change["category"] for change in result_a["changes"]} >= {"text", "table", "structure"}
