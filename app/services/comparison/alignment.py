# mypy: ignore-errors
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np
from PIL import Image


@dataclass(frozen=True)
class AlignmentResult:
    image: Image.Image
    matrix: list[list[float]]
    confidence: float
    method: str
    match_count: int


def align_to_reference(reference: Image.Image, candidate: Image.Image) -> AlignmentResult:
    ref = np.array(reference.convert("L"))
    cand = np.array(candidate.convert("L").resize(reference.size))

    orb_result = _orb_align(ref, cand)
    if orb_result is not None and orb_result.confidence >= 0.5:
        return orb_result

    return _phase_align(ref, cand)


def refine_with_ecc(reference: Image.Image, candidate: Image.Image) -> AlignmentResult:
    ref = np.array(reference.convert("L"), dtype=np.float32) / 255.0
    cand = np.array(candidate.convert("L").resize(reference.size), dtype=np.float32) / 255.0
    matrix = np.eye(2, 3, dtype=np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 50, 1e-5)
    try:
        confidence, refined = cv2.findTransformECC(
            ref,
            cand,
            matrix,
            cv2.MOTION_TRANSLATION,
            criteria,
        )
    except cv2.error:
        return align_to_reference(reference, candidate)

    height, width = ref.shape[:2]
    aligned = cv2.warpAffine(
        np.array(candidate.convert("L").resize(reference.size)),
        refined,
        (width, height),
        flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return AlignmentResult(
        image=Image.fromarray(aligned).convert("L"),
        matrix=_matrix_to_list(refined),
        confidence=round(max(0.0, min(float(confidence), 1.0)), 3),
        method="ecc_translation",
        match_count=0,
    )


def _orb_align(reference: np.ndarray, candidate: np.ndarray) -> AlignmentResult | None:
    orb = cv2.ORB_create(nfeatures=1000)
    keypoints_a, descriptors_a = orb.detectAndCompute(reference, None)
    keypoints_b, descriptors_b = orb.detectAndCompute(candidate, None)
    if (
        descriptors_a is None
        or descriptors_b is None
        or len(keypoints_a) < 8
        or len(keypoints_b) < 8
    ):
        return None

    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = sorted(matcher.match(descriptors_a, descriptors_b), key=lambda match: match.distance)
    if len(matches) < 8:
        return None

    source = np.float32([keypoints_b[match.trainIdx].pt for match in matches]).reshape(-1, 1, 2)
    target = np.float32([keypoints_a[match.queryIdx].pt for match in matches]).reshape(-1, 1, 2)
    matrix, mask = cv2.findHomography(source, target, cv2.RANSAC, 5.0)
    if matrix is None or mask is None:
        return None

    height, width = reference.shape[:2]
    aligned = cv2.warpPerspective(
        candidate,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )
    inlier_count = int(mask.sum())
    confidence = inlier_count / len(matches)
    return AlignmentResult(
        image=Image.fromarray(aligned).convert("L"),
        matrix=_matrix_to_list(matrix),
        confidence=round(confidence, 3),
        method="orb_homography",
        match_count=len(matches),
    )


def _phase_align(reference: np.ndarray, candidate: np.ndarray) -> AlignmentResult:
    shift, response = cv2.phaseCorrelate(np.float32(reference), np.float32(candidate))
    dx, dy = shift
    matrix = np.array([[1.0, 0.0, dx], [0.0, 1.0, dy]], dtype=np.float32)
    height, width = reference.shape[:2]
    aligned = cv2.warpAffine(
        candidate,
        matrix,
        (width, height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return AlignmentResult(
        image=Image.fromarray(aligned).convert("L"),
        matrix=_matrix_to_list(matrix),
        confidence=round(max(0.0, min(float(response), 1.0)), 3),
        method="phase_correlation",
        match_count=0,
    )


def _matrix_to_list(matrix: np.ndarray) -> list[list[float]]:
    return [[round(float(value), 6) for value in row] for row in matrix.tolist()]


def alignment_diagnostics(result: AlignmentResult, page: int) -> dict[str, Any]:
    return {
        "page": page,
        "method": result.method,
        "confidence": result.confidence,
        "match_count": result.match_count,
        "matrix": result.matrix,
    }
