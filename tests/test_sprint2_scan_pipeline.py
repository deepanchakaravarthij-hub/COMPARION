from __future__ import annotations

from io import BytesIO

import cv2
import numpy as np
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.main import app
from app.services.compare_service import compare_files
from app.services.comparison.alignment import align_to_reference
from app.services.comparison.ocr import OcrToken, build_ocr_result, filter_tokens
from app.services.comparison.preprocessing import (
    detect_orientation,
    estimate_skew,
    preprocess_image,
)

client = TestClient(app)


def _scan_image(mark_offset: int = 0) -> Image.Image:
    image = Image.new("L", (80, 120), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((18 + mark_offset, 20, 62 + mark_offset, 28), fill="black")
    draw.rectangle((18 + mark_offset, 42, 58 + mark_offset, 50), fill="black")
    draw.rectangle((18 + mark_offset, 64, 52 + mark_offset, 72), fill="black")
    return image


def _png_bytes(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_orientation_detection_for_landscape_scan() -> None:
    rotated = _scan_image().rotate(90, expand=True)
    gray = np.array(rotated.convert("L"))
    assert detect_orientation(gray) == 270


def test_preprocess_corrects_rotated_scan_to_portrait() -> None:
    rotated = _scan_image().rotate(90, expand=True)
    processed = preprocess_image(rotated)
    assert processed.metadata.rotation_degrees == 270
    assert processed.image.height > processed.image.width


def test_skew_estimation_detects_skewed_scan() -> None:
    image = _scan_image()
    matrix = cv2.getRotationMatrix2D((40, 60), 8, 1.0)
    skewed = cv2.warpAffine(  # type: ignore[call-overload]
        np.array(image),
        matrix,
        (80, 120),
        borderValue=255,
    )
    angle = estimate_skew(skewed)
    assert abs(angle) > 1


def test_ocr_confidence_filtering_and_grouping() -> None:
    tokens = [
        OcrToken("Keep", 0.95, (0.1, 0.1, 0.2, 0.1)),
        OcrToken("drop", 0.2, (0.4, 0.1, 0.2, 0.1)),
    ]
    filtered = filter_tokens(tokens, threshold=0.6)
    result = build_ocr_result(filtered)
    assert result.text == "Keep"
    assert result.confidence == 0.95


def test_alignment_handles_shifted_scan() -> None:
    reference = _scan_image()
    shifted = _scan_image(mark_offset=4)
    alignment = align_to_reference(reference, shifted)
    assert alignment.method in {"orb_homography", "phase_correlation"}
    assert alignment.image.size == reference.size
    assert alignment.matrix


def test_rotated_scan_comparison_reduces_false_positive_noise() -> None:
    original = _scan_image()
    rotated = original.rotate(90, expand=True)
    result = compare_files("a.png", "b.png", _png_bytes(original), _png_bytes(rotated))
    assert result["file_type"] == "image"
    assert result["result_schema_version"] == "2.0"
    assert result["diagnostics"]["preprocessing"][1]["rotation_degrees"] == 270
    assert len(result["changes"]) <= 1


def test_scan_api_returns_diagnostics() -> None:
    original = _scan_image()
    rotated = original.rotate(90, expand=True)
    files = {
        "file_a": ("a.png", _png_bytes(original), "image/png"),
        "file_b": ("b.png", _png_bytes(rotated), "image/png"),
    }
    compare_res = client.post("/v1/compare", files=files)
    assert compare_res.status_code == 200
    job_id = compare_res.json()["job_id"]
    result_res = client.get(f"/v1/jobs/{job_id}/result")
    assert result_res.status_code == 200
    payload = result_res.json()
    assert payload["diagnostics"]["alignment"]
    assert payload["diagnostics"]["debug_artifacts"]
