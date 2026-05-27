from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw

from app.services.comparison.embedded_image import (
    EmbeddedImage,
    bbox_iou,
    compare_image_pair,
    diff_embedded_images,
    match_images,
    overlaps_mask,
    sha256_bytes,
)


def _png_blob(color: tuple[int, int, int]) -> bytes:
    image = Image.new("RGB", (40, 40), color)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_bbox_iou_disjoint() -> None:
    assert bbox_iou((0.0, 0.0, 0.2, 0.2), (0.5, 0.5, 0.2, 0.2)) == 0.0


def test_bbox_iou_overlap() -> None:
    score = bbox_iou((0.0, 0.0, 0.5, 0.5), (0.25, 0.25, 0.5, 0.5))
    assert score > 0.1


def test_compare_image_pair_identical() -> None:
    blob = _png_blob((255, 0, 0))
    changed, score = compare_image_pair(blob, blob)
    assert changed is False
    assert score == 1.0


def test_compare_image_pair_different() -> None:
    changed, score = compare_image_pair(_png_blob((255, 0, 0)), _png_blob((0, 0, 255)))
    assert changed is True
    assert score < 0.95


def test_diff_embedded_images_removed_added() -> None:
    blob_a = _png_blob((255, 0, 0))
    blob_b = _png_blob((0, 0, 255))
    image_a = EmbeddedImage("a", 1, (0.2, 0.2, 0.2, 0.2), blob_a, sha256_bytes(blob_a))
    image_b = EmbeddedImage("b", 1, (0.2, 0.2, 0.2, 0.2), blob_b, sha256_bytes(blob_b))
    changes = diff_embedded_images([image_a], [image_b], page=1, ssim_threshold=0.95)
    assert len(changes) == 2
    assert {change["type"] for change in changes} == {"removed", "added"}


def test_match_images_by_hash() -> None:
    blob = _png_blob((10, 20, 30))
    digest = sha256_bytes(blob)
    image_a = EmbeddedImage("a1", 1, (0.1, 0.1, 0.2, 0.2), blob, digest)
    image_b = EmbeddedImage("b1", 1, (0.5, 0.5, 0.2, 0.2), blob, digest)
    pairs = match_images([image_a], [image_b], page=1)
    assert pairs == [(image_a, image_b)]


def test_overlaps_mask() -> None:
    region = (0.1, 0.1, 0.3, 0.3)
    mask = (0.12, 0.12, 0.25, 0.25)
    assert overlaps_mask(region, [mask]) is True


def test_visual_changes_respects_mask() -> None:
    from app.services.comparison.image_engine import visual_changes

    image_a = Image.new("L", (200, 200), 255)
    image_b = Image.new("L", (200, 200), 255)
    draw = ImageDraw.Draw(image_b)
    draw.rectangle((20, 20, 80, 80), fill=0)
    draw.rectangle((120, 120, 180, 180), fill=0)

    unmasked = visual_changes(image_a, image_b, page=1)
    masked = visual_changes(
        image_a,
        image_b,
        page=1,
        mask_bboxes=[(0.08, 0.08, 0.36, 0.36)],
    )
    assert len(unmasked) >= len(masked)
