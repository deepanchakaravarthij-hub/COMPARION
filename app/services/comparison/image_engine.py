from __future__ import annotations

from io import BytesIO
from typing import Any

import numpy as np
from PIL import Image, ImageChops
from skimage.metrics import structural_similarity


def load_normalized_image(content: bytes, size: tuple[int, int] | None = None) -> Image.Image:
    image = Image.open(BytesIO(content)).convert("L")
    if size:
        image = image.resize(size)
    return image


def visual_change(
    image_a: Image.Image,
    image_b: Image.Image,
    page: int = 1,
) -> dict[str, Any] | None:
    target_size = (
        max(image_a.width, image_b.width),
        max(image_a.height, image_b.height),
    )
    normalized_a = image_a.resize(target_size)
    normalized_b = image_b.resize(target_size)
    diff = ImageChops.difference(normalized_a, normalized_b)
    bbox = diff.getbbox()

    if bbox is None:
        return None

    ssim_score = float(
        structural_similarity(  # type: ignore[no-untyped-call]
            np.array(normalized_a),
            np.array(normalized_b),
            data_range=255,
        )
    )
    left, top, right, bottom = bbox
    changed_pixels = sum(count for value, count in enumerate(diff.histogram()) if value)
    total_pixels = target_size[0] * target_size[1]
    ratio = changed_pixels / total_pixels if total_pixels else 0

    return {
        "type": "modified",
        "category": "visual",
        "severity": "high" if ratio > 0.05 else "low",
        "confidence": round(min(0.99, max(0.5, 1 - ssim_score)), 3),
        "message": f"Visual difference detected on page {page}",
        "source_ref": {"document": "both", "page": page},
        "bbox": {
            "page": page,
            "x": left / target_size[0],
            "y": top / target_size[1],
            "width": (right - left) / target_size[0],
            "height": (bottom - top) / target_size[1],
        },
    }
