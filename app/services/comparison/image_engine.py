from __future__ import annotations

from io import BytesIO
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageChops
from skimage.metrics import structural_similarity

from app.services.comparison.embedded_image import overlaps_mask


def load_normalized_image(content: bytes, size: tuple[int, int] | None = None) -> Image.Image:
    image = Image.open(BytesIO(content)).convert("L")
    if size:
        image = image.resize(size)
    return image


def _normalize_bbox(
    left: int,
    top: int,
    right: int,
    bottom: int,
    width: int,
    height: int,
    page: int,
    *,
    pad_ratio: float = 0.004,
) -> dict[str, float | int]:
    pad_x = max(1, int(width * pad_ratio))
    pad_y = max(1, int(height * pad_ratio))
    left = max(0, left - pad_x)
    top = max(0, top - pad_y)
    right = min(width, right + pad_x)
    bottom = min(height, bottom + pad_y)
    return {
        "page": page,
        "x": left / width,
        "y": top / height,
        "width": (right - left) / width,
        "height": (bottom - top) / height,
    }


def _region_category(
    left: int,
    top: int,
    right: int,
    bottom: int,
    width: int,
    height: int,
) -> str:
    area_ratio = ((right - left) * (bottom - top)) / (width * height) if width and height else 0.0
    if 0.001 <= area_ratio <= 0.4:
        return "image"
    return "visual"


def _region_change(
    left: int,
    top: int,
    right: int,
    bottom: int,
    width: int,
    height: int,
    page: int,
    *,
    ratio: float,
    confidence: float,
    region_index: int,
    total_regions: int,
) -> dict[str, Any]:
    category = _region_category(left, top, right, bottom, width, height)
    label = "Image" if category == "image" else "Visual"
    message = f"{label} difference detected on page {page}"
    if total_regions > 1:
        message = f"{message} (region {region_index} of {total_regions})"
    return {
        "type": "modified",
        "category": category,
        "severity": "high" if ratio > 0.05 else "medium" if ratio > 0.01 else "low",
        "confidence": confidence,
        "message": message,
        "source_ref": {"document": "both", "page": page},
        "bbox": _normalize_bbox(left, top, right, bottom, width, height, page),
    }


def visual_changes(
    image_a: Image.Image,
    image_b: Image.Image,
    page: int = 1,
    *,
    diff_threshold: int = 24,
    min_region_pixels: int = 120,
    max_regions: int = 40,
    max_region_area_ratio: float = 0.85,
    mask_bboxes: list[tuple[float, float, float, float]] | None = None,
    mask_iou_threshold: float = 0.15,
) -> list[dict[str, Any]]:
    """Detect localized visual differences and return one change per region."""
    target_size = (
        max(image_a.width, image_b.width),
        max(image_a.height, image_b.height),
    )
    width, height = target_size
    normalized_a = image_a.resize(target_size)
    normalized_b = image_b.resize(target_size)
    diff = ImageChops.difference(normalized_a, normalized_b)
    diff_array = np.array(diff, dtype=np.uint8)

    changed_pixels = int(np.count_nonzero(diff_array > diff_threshold))
    total_pixels = width * height
    if changed_pixels == 0:
        return []

    ratio = changed_pixels / total_pixels if total_pixels else 0.0
    ssim_score = float(
        structural_similarity(  # type: ignore[no-untyped-call]
            np.array(normalized_a),
            np.array(normalized_b),
            data_range=255,
        )
    )
    confidence = round(min(0.99, max(0.5, 1 - ssim_score)), 3)

    mask = (diff_array > diff_threshold).astype(np.uint8)
    _, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)

    regions: list[tuple[int, int, int, int, int]] = []
    for label in range(1, stats.shape[0]):
        x, y, w, h, area = stats[label]
        if area < min_region_pixels:
            continue
        if area / total_pixels > max_region_area_ratio:
            continue
        regions.append((x, y, x + w, y + h, area))

    regions.sort(key=lambda item: item[4], reverse=True)
    regions = regions[:max_regions]

    if mask_bboxes:
        filtered: list[tuple[int, int, int, int, int]] = []
        for left, top, right, bottom, area in regions:
            norm = (
                left / width,
                top / height,
                (right - left) / width,
                (bottom - top) / height,
            )
            if overlaps_mask(norm, mask_bboxes, min_iou=mask_iou_threshold):
                continue
            filtered.append((left, top, right, bottom, area))
        regions = filtered

    if not regions:
        bbox = diff.getbbox()
        if bbox is None:
            return []
        left, top, right, bottom = bbox
        region_ratio = ((right - left) * (bottom - top)) / total_pixels if total_pixels else ratio
        if region_ratio > max_region_area_ratio:
            return []
        return [
            _region_change(
                left,
                top,
                right,
                bottom,
                width,
                height,
                page,
                ratio=ratio,
                confidence=confidence,
                region_index=1,
                total_regions=1,
            )
        ]

    total_regions = len(regions)
    return [
        _region_change(
            left,
            top,
            right,
            bottom,
            width,
            height,
            page,
            ratio=ratio,
            confidence=confidence,
            region_index=index,
            total_regions=total_regions,
        )
        for index, (left, top, right, bottom, _) in enumerate(regions, start=1)
    ]


def visual_change(
    image_a: Image.Image,
    image_b: Image.Image,
    page: int = 1,
) -> dict[str, Any] | None:
    changes = visual_changes(image_a, image_b, page=page)
    if not changes:
        return None
    if len(changes) == 1:
        return changes[0]
    return {
        "type": "modified",
        "category": "visual",
        "severity": changes[0]["severity"],
        "confidence": changes[0]["confidence"],
        "message": f"Visual differences detected on page {page} ({len(changes)} regions)",
        "source_ref": {"document": "both", "page": page},
        "bbox": changes[0]["bbox"],
    }
