from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


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


def test_compare_and_result() -> None:
    files = {
        "file_a": ("a.pdf", b"hello", "application/pdf"),
        "file_b": ("b.pdf", b"hello2", "application/pdf"),
    }
    compare_res = client.post("/v1/compare", files=files)
    assert compare_res.status_code == 200

    job_id = compare_res.json()["job_id"]
    status_res = client.get(f"/v1/jobs/{job_id}")
    assert status_res.status_code == 200

    result_res = client.get(f"/v1/jobs/{job_id}/result")
    assert result_res.status_code == 200
    payload = result_res.json()
    assert payload["file_type"] == "pdf"
    assert "Differences detected" in payload["summary"]
