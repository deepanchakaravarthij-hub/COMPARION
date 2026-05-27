from __future__ import annotations

import hashlib
from dataclasses import dataclass
from io import BytesIO
from typing import Any

import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity


@dataclass(frozen=True)
class EmbeddedImage:
    image_id: str
    page: int
    bbox: tuple[float, float, float, float]
    blob: bytes
    sha256: str
    kind: str = "image"


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def bbox_iou(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    a_right, a_bottom = ax + aw, ay + ah
    b_right, b_bottom = bx + bw, by + bh
    inter_left = max(ax, bx)
    inter_top = max(ay, by)
    inter_right = min(a_right, b_right)
    inter_bottom = min(a_bottom, b_bottom)
    if inter_right <= inter_left or inter_bottom <= inter_top:
        return 0.0
    inter_area = (inter_right - inter_left) * (inter_bottom - inter_top)
    union = aw * ah + bw * bh - inter_area
    if union <= 0:
        return 0.0
    return inter_area / union


def bboxes_from_changes(changes: list[dict[str, Any]]) -> list[tuple[float, float, float, float]]:
    boxes: list[tuple[float, float, float, float]] = []
    for change in changes:
        bbox = change.get("bbox")
        if not isinstance(bbox, dict):
            continue
        x = float(bbox.get("x", 0))
        y = float(bbox.get("y", 0))
        width = float(bbox.get("width", 0))
        height = float(bbox.get("height", 0))
        if width > 0 and height > 0:
            boxes.append((x, y, width, height))
    return boxes


def overlaps_mask(
    bbox: tuple[float, float, float, float],
    masks: list[tuple[float, float, float, float]],
    *,
    min_iou: float = 0.15,
) -> bool:
    return any(bbox_iou(bbox, mask) >= min_iou for mask in masks)


def compare_image_pair(
    blob_a: bytes,
    blob_b: bytes,
    *,
    ssim_threshold: float = 0.95,
) -> tuple[bool, float]:
    if sha256_bytes(blob_a) == sha256_bytes(blob_b):
        return False, 1.0
    try:
        image_a = Image.open(BytesIO(blob_a)).convert("L")
        image_b = Image.open(BytesIO(blob_b)).convert("L")
    except OSError:
        return True, 0.5
    size = (
        max(image_a.width, image_b.width),
        max(image_a.height, image_b.height),
    )
    if size[0] == 0 or size[1] == 0:
        return True, 0.5
    array_a = np.array(image_a.resize(size), dtype=np.uint8)
    array_b = np.array(image_b.resize(size), dtype=np.uint8)
    score = float(
        structural_similarity(  # type: ignore[no-untyped-call]
            array_a,
            array_b,
            data_range=255,
        )
    )
    return score < ssim_threshold, round(score, 3)


def match_images(
    images_a: list[EmbeddedImage],
    images_b: list[EmbeddedImage],
    *,
    page: int | None = None,
    iou_threshold: float = 0.2,
) -> list[tuple[EmbeddedImage | None, EmbeddedImage | None]]:
    pool_a = [image for image in images_a if page is None or image.page == page]
    pool_b = [image for image in images_b if page is None or image.page == page]
    remaining_b = list(pool_b)
    pairs: list[tuple[EmbeddedImage | None, EmbeddedImage | None]] = []

    for image_a in pool_a:
        best: EmbeddedImage | None = None
        best_score = -1.0
        for candidate in remaining_b:
            if candidate.sha256 == image_a.sha256:
                best = candidate
                best_score = 2.0
                break
            score = bbox_iou(image_a.bbox, candidate.bbox)
            if score > best_score:
                best_score = score
                best = candidate
        if best is not None and best_score >= iou_threshold:
            remaining_b.remove(best)
            pairs.append((image_a, best))
        else:
            pairs.append((image_a, None))

    for image_b in remaining_b:
        pairs.append((None, image_b))
    return pairs


def _embedded_image_change(
    change_type: str,
    document: str,
    image: EmbeddedImage,
    *,
    message: str,
    confidence: float,
) -> dict[str, Any]:
    x, y, width, height = image.bbox
    return {
        "type": change_type,
        "category": "image",
        "severity": "medium",
        "confidence": confidence,
        "message": message,
        "source_ref": {"document": document, "page": image.page, "slide": image.page},
        "bbox": {
            "page": image.page,
            "x": round(x, 4),
            "y": round(y, 4),
            "width": round(width, 4),
            "height": round(height, 4),
        },
    }


def diff_embedded_images(
    images_a: list[EmbeddedImage],
    images_b: list[EmbeddedImage],
    *,
    page: int | None = None,
    ssim_threshold: float = 0.95,
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    for image_a, image_b in match_images(images_a, images_b, page=page):
        if image_a is not None and image_b is not None:
            if image_a.sha256 == image_b.sha256:
                continue
            changed, confidence = compare_image_pair(
                image_a.blob,
                image_b.blob,
                ssim_threshold=ssim_threshold,
            )
            if not changed:
                continue
            message = f"Image changed on page {image_a.page}"
            changes.append(
                _embedded_image_change(
                    "removed",
                    "a",
                    image_a,
                    message=message,
                    confidence=confidence,
                )
            )
            changes.append(
                _embedded_image_change(
                    "added",
                    "b",
                    image_b,
                    message=message,
                    confidence=confidence,
                )
            )
        elif image_a is not None:
            changes.append(
                _embedded_image_change(
                    "removed",
                    "a",
                    image_a,
                    message=f"Image removed on page {image_a.page}",
                    confidence=0.9,
                )
            )
        elif image_b is not None:
            changes.append(
                _embedded_image_change(
                    "added",
                    "b",
                    image_b,
                    message=f"Image added on page {image_b.page}",
                    confidence=0.9,
                )
            )
    return changes
