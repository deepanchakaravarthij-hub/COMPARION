from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BenchmarkMetrics:
    change_count: int
    false_positive_count: int
    runtime_ms: float
    ocr_confidence: float


def summarize_metrics(
    change_count: int,
    runtime_ms: float,
    ocr_confidences: list[float],
    expected_change_count: int | None = None,
) -> BenchmarkMetrics:
    false_positive_count = 0
    if expected_change_count is not None:
        false_positive_count = max(0, change_count - expected_change_count)
    confidence = sum(ocr_confidences) / len(ocr_confidences) if ocr_confidences else 0.0
    return BenchmarkMetrics(
        change_count=change_count,
        false_positive_count=false_positive_count,
        runtime_ms=round(runtime_ms, 2),
        ocr_confidence=round(confidence, 3),
    )
