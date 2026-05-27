from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.services.comparison.embedded_image import EmbeddedImage, diff_embedded_images, sha256_bytes
from app.services.comparison.pptx_parser import PptxObject, PptxSlide, parse_pptx


def compare_pptx_presentations(
    content_a: bytes,
    content_b: bytes,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    presentation_a = parse_pptx(content_a)
    presentation_b = parse_pptx(content_b)

    changes: list[dict[str, Any]] = []
    changed_objects: list[dict[str, Any]] = []

    matches, removed_slides, added_slides = _match_slides(
        presentation_a.slides,
        presentation_b.slides,
    )

    slide_width = max(presentation_a.slide_width_emu, presentation_b.slide_width_emu, 1)
    slide_height = max(presentation_a.slide_height_emu, presentation_b.slide_height_emu, 1)

    for slide in removed_slides:
        changes.append(
            _structure_change(
                "removed",
                f"Slide removed at position {slide.index}",
                {"document": "a", "slide": slide.index},
                slide.index,
            )
        )
    for slide in added_slides:
        changes.append(
            _structure_change(
                "added",
                f"Slide added at position {slide.index}",
                {"document": "b", "slide": slide.index},
                slide.index,
            )
        )

    for slide_a, slide_b in matches:
        if slide_a.index != slide_b.index:
            changes.append(
                _structure_change(
                    "modified",
                    f"Slide reordered from {slide_a.index} to {slide_b.index}",
                    {"document": "both", "slide": slide_a.index},
                    slide_a.index,
                )
            )
        _append_object_changes(
            changes,
            changed_objects,
            slide_a,
            slide_b,
            slide_width,
            slide_height,
        )

    diagnostics = {
        "slide_count": {"a": len(presentation_a.slides), "b": len(presentation_b.slides)},
        "slide_summary": [
            {
                "slide_a": slide_a.index,
                "slide_b": slide_b.index,
                "title_a": slide_a.title,
                "title_b": slide_b.title,
                "objects_a": len(slide_a.objects),
                "objects_b": len(slide_b.objects),
            }
            for slide_a, slide_b in matches
        ],
        "changed_objects": changed_objects,
    }
    return changes, diagnostics


def _append_object_changes(
    changes: list[dict[str, Any]],
    changed_objects: list[dict[str, Any]],
    slide_a: PptxSlide,
    slide_b: PptxSlide,
    slide_width: int,
    slide_height: int,
) -> None:
    settings = get_settings()
    changes.extend(
        diff_embedded_images(
            _pptx_images_to_embedded(slide_a.objects, slide_a.index, slide_width, slide_height),
            _pptx_images_to_embedded(slide_b.objects, slide_b.index, slide_width, slide_height),
            page=slide_a.index,
            ssim_threshold=settings.image_ssim_threshold,
        )
    )

    non_image_a = [object_ for object_ in slide_a.objects if object_.kind != "image"]
    non_image_b = [object_ for object_ in slide_b.objects if object_.kind != "image"]
    for object_a, object_b in _match_objects_by_signature(non_image_a, non_image_b):
        if object_a is None and object_b is not None:
            changes.append(
                _object_change(
                    "added",
                    _category_for_kind(object_b.kind),
                    f"Object added on slide {slide_b.index}: {object_b.kind}",
                    {"document": "b", "slide": slide_b.index},
                    object_b,
                    slide_width,
                    slide_height,
                )
            )
            changed_objects.append(_changed_object("added", slide_b.index, None, object_b))
            continue
        if object_b is None and object_a is not None:
            changes.append(
                _object_change(
                    "removed",
                    _category_for_kind(object_a.kind),
                    f"Object removed on slide {slide_a.index}: {object_a.kind}",
                    {"document": "a", "slide": slide_a.index},
                    object_a,
                    slide_width,
                    slide_height,
                )
            )
            changed_objects.append(_changed_object("removed", slide_a.index, object_a, None))
            continue
        if object_a is None or object_b is None:
            continue
        _compare_object_pair(
            changes,
            changed_objects,
            slide_a,
            slide_b,
            object_a,
            object_b,
            slide_width,
            slide_height,
        )


def _pptx_images_to_embedded(
    objects: list[PptxObject],
    slide_index: int,
    slide_width: int,
    slide_height: int,
) -> list[EmbeddedImage]:
    embedded: list[EmbeddedImage] = []
    for object_ in objects:
        if object_.kind != "image" or not object_.image_blob or not object_.bbox:
            continue
        left, top, width, height = object_.bbox
        embedded.append(
            EmbeddedImage(
                image_id=object_.object_id,
                page=slide_index,
                bbox=(
                    left / slide_width,
                    top / slide_height,
                    width / slide_width,
                    height / slide_height,
                ),
                blob=object_.image_blob,
                sha256=object_.image_sha256 or sha256_bytes(object_.image_blob),
            )
        )
    return embedded


def _object_match_key(object_: PptxObject) -> str:
    if object_.kind == "text":
        return f"text|{object_.text}"
    if object_.kind == "table":
        return f"table|{object_.table_cells}"
    return object_.content_signature


def _match_objects_by_signature(
    objects_a: list[PptxObject],
    objects_b: list[PptxObject],
) -> list[tuple[PptxObject | None, PptxObject | None]]:
    remaining_b = list(objects_b)
    pairs: list[tuple[PptxObject | None, PptxObject | None]] = []
    for object_a in objects_a:
        match = next(
            (candidate for candidate in remaining_b if _object_match_key(candidate) == _object_match_key(object_a)),
            None,
        )
        if match is not None:
            remaining_b.remove(match)
            pairs.append((object_a, match))
        else:
            pairs.append((object_a, None))
    for object_b in remaining_b:
        pairs.append((None, object_b))
    return pairs


def _compare_object_pair(
    changes: list[dict[str, Any]],
    changed_objects: list[dict[str, Any]],
    slide_a: PptxSlide,
    slide_b: PptxSlide,
    object_a: PptxObject,
    object_b: PptxObject,
    slide_width: int,
    slide_height: int,
) -> None:
    if object_a.kind != object_b.kind:
        changes.append(
            _change(
                "modified",
                "structure",
                "medium",
                0.88,
                f"Object type changed on slide {slide_a.index}: {object_a.kind} -> {object_b.kind}",
                {"document": "both", "slide": slide_a.index},
            )
        )
        changed_objects.append(_changed_object("kind", slide_a.index, object_a, object_b))
        return

    if object_a.kind == "text":
        message = (
            f"Text changed on slide {slide_a.index}: "
            f"{object_a.text!r} -> {object_b.text!r}"
        )
        if object_a.text != object_b.text:
            changes.append(
                _object_change(
                    "removed",
                    "text",
                    message,
                    {"document": "a", "slide": slide_a.index},
                    object_a,
                    slide_width,
                    slide_height,
                )
            )
            changes.append(
                _object_change(
                    "added",
                    "text",
                    message,
                    {"document": "b", "slide": slide_b.index},
                    object_b,
                    slide_width,
                    slide_height,
                )
            )
            changed_objects.append(_changed_object("text", slide_a.index, object_a, object_b))
        elif object_a.style_signature != object_b.style_signature:
            changes.append(
                _object_change(
                    "modified",
                    "formatting",
                    f"Text style changed on slide {slide_a.index}",
                    {"document": "both", "slide": slide_a.index},
                    object_a,
                    slide_width,
                    slide_height,
                )
            )
            changed_objects.append(_changed_object("formatting", slide_a.index, object_a, object_b))
    elif object_a.kind == "table":
        if object_a.table_cells != object_b.table_cells:
            changes.append(
                _object_change(
                    "removed",
                    "table",
                    f"Table changed on slide {slide_a.index}",
                    {"document": "a", "slide": slide_a.index},
                    object_a,
                    slide_width,
                    slide_height,
                )
            )
            changes.append(
                _object_change(
                    "added",
                    "table",
                    f"Table changed on slide {slide_b.index}",
                    {"document": "b", "slide": slide_b.index},
                    object_b,
                    slide_width,
                    slide_height,
                )
            )
            changed_objects.append(_changed_object("table", slide_a.index, object_a, object_b))
    elif object_a.shape_signature != object_b.shape_signature or object_a.text != object_b.text:
        changes.append(
            _object_change(
                "removed",
                "structure",
                f"Shape changed on slide {slide_a.index}",
                {"document": "a", "slide": slide_a.index},
                object_a,
                slide_width,
                slide_height,
            )
        )
        changes.append(
            _object_change(
                "added",
                "structure",
                f"Shape changed on slide {slide_b.index}",
                {"document": "b", "slide": slide_b.index},
                object_b,
                slide_width,
                slide_height,
            )
        )
        changed_objects.append(_changed_object("shape", slide_a.index, object_a, object_b))

    if object_a.bbox != object_b.bbox and object_a.bbox and object_b.bbox:
        changes.append(
            _object_change(
                "modified",
                "visual",
                f"Object position changed on slide {slide_a.index}",
                {"document": "both", "slide": slide_a.index},
                object_a,
                slide_width,
                slide_height,
            )
        )


def _match_slides(
    slides_a: list[PptxSlide],
    slides_b: list[PptxSlide],
) -> tuple[list[tuple[PptxSlide, PptxSlide]], list[PptxSlide], list[PptxSlide]]:
    remaining_b = slides_b.copy()
    matches: list[tuple[PptxSlide, PptxSlide]] = []

    for slide_a in slides_a:
        match = next(
            (slide for slide in remaining_b if slide.fingerprint == slide_a.fingerprint),
            None,
        )
        if match is not None:
            matches.append((slide_a, match))
            remaining_b.remove(match)

    unmatched_a = [slide for slide in slides_a if slide not in [pair[0] for pair in matches]]
    for slide_a in unmatched_a:
        title_match = next(
            (slide for slide in remaining_b if _titles_match(slide_a.title, slide.title)),
            None,
        )
        if title_match is not None:
            matches.append((slide_a, title_match))
            remaining_b.remove(title_match)

    unmatched_a = [slide for slide in slides_a if slide not in [pair[0] for pair in matches]]
    for slide_a in unmatched_a:
        by_index = next((slide for slide in remaining_b if slide.index == slide_a.index), None)
        if by_index is not None:
            matches.append((slide_a, by_index))
            remaining_b.remove(by_index)

    used_a = [pair[0] for pair in matches]
    removed_slides = [slide for slide in slides_a if slide not in used_a]
    added_slides = remaining_b
    matches.sort(key=lambda pair: pair[0].index)
    return matches, removed_slides, added_slides


def _structure_change(
    change_type: str,
    message: str,
    source_ref: dict[str, Any],
    slide_index: int,
) -> dict[str, Any]:
    source_ref = {**source_ref, "page": slide_index}
    payload = _change(
        change_type,
        "structure",
        "high",
        0.95,
        message,
        source_ref,
    )
    payload["bbox"] = {
        "page": slide_index,
        "x": 0.0,
        "y": 0.0,
        "width": 1.0,
        "height": 1.0,
    }
    return payload


def _object_change(
    change_type: str,
    category: str,
    message: str,
    source_ref: dict[str, Any],
    object_: PptxObject,
    slide_width: int,
    slide_height: int,
) -> dict[str, Any]:
    slide_index = int(source_ref["slide"])
    source_ref = {**source_ref, "page": slide_index}
    payload = _change(
        change_type,
        category,
        _severity(category),
        _confidence(category),
        message,
        source_ref,
    )
    if object_.bbox:
        left, top, width, height = object_.bbox
        payload["bbox"] = {
            "page": slide_index,
            "x": round(left / slide_width, 4),
            "y": round(top / slide_height, 4),
            "width": round(width / slide_width, 4),
            "height": round(height / slide_height, 4),
        }
    return payload


def _changed_object(
    kind: str,
    slide: int,
    old_object: PptxObject | None,
    new_object: PptxObject | None,
) -> dict[str, Any]:
    return {
        "slide": slide,
        "kind": kind,
        "object_a": old_object.object_id if old_object else None,
        "object_b": new_object.object_id if new_object else None,
        "type_a": old_object.kind if old_object else None,
        "type_b": new_object.kind if new_object else None,
    }


def _severity(category: str) -> str:
    if category in {"image", "table", "structure"}:
        return "high"
    if category in {"text", "visual"}:
        return "medium"
    return "low"


def _confidence(category: str) -> float:
    if category in {"text", "table", "image"}:
        return 0.94
    if category == "visual":
        return 0.88
    return 0.85


def _category_for_kind(kind: str) -> str:
    if kind == "table":
        return "table"
    if kind == "image":
        return "image"
    if kind == "text":
        return "text"
    return "structure"


def _titles_match(title_a: str | None, title_b: str | None) -> bool:
    if not title_a or not title_b:
        return False
    left = " ".join(title_a.lower().split())
    right = " ".join(title_b.lower().split())
    return left == right or left in right or right in left


def _change(
    change_type: str,
    category: str,
    severity: str,
    confidence: float,
    message: str,
    source_ref: dict[str, Any],
) -> dict[str, Any]:
    return {
        "type": change_type,
        "category": category,
        "severity": severity,
        "confidence": confidence,
        "message": message,
        "source_ref": source_ref,
    }
