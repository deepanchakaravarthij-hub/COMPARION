from __future__ import annotations

from typing import Any

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

    for slide in removed_slides:
        changes.append(
            _change(
                "removed",
                "structure",
                "high",
                0.95,
                f"Slide removed at position {slide.index}",
                {"document": "a", "slide": slide.index},
            )
        )
    for slide in added_slides:
        changes.append(
            _change(
                "added",
                "structure",
                "high",
                0.95,
                f"Slide added at position {slide.index}",
                {"document": "b", "slide": slide.index},
            )
        )

    for slide_a, slide_b in matches:
        if slide_a.index != slide_b.index:
            changes.append(
                _change(
                    "modified",
                    "structure",
                    "medium",
                    0.9,
                    f"Slide reordered from {slide_a.index} to {slide_b.index}",
                    {"document": "both", "slide": slide_a.index},
                )
            )
        _append_object_changes(changes, changed_objects, slide_a, slide_b)

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
) -> None:
    max_objects = max(len(slide_a.objects), len(slide_b.objects))
    for index in range(max_objects):
        object_a = slide_a.objects[index] if index < len(slide_a.objects) else None
        object_b = slide_b.objects[index] if index < len(slide_b.objects) else None

        if object_a is None and object_b is not None:
            changes.append(
                _object_change(
                    "added",
                    _category_for_kind(object_b.kind),
                    f"Object added on slide {slide_b.index}: {object_b.kind}",
                    {"document": "b", "slide": slide_b.index},
                    object_b,
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
                )
            )
            changed_objects.append(_changed_object("removed", slide_a.index, object_a, None))
            continue
        if object_a is None or object_b is None:
            continue

        _compare_object_pair(changes, changed_objects, slide_a, slide_b, object_a, object_b)


def _compare_object_pair(
    changes: list[dict[str, Any]],
    changed_objects: list[dict[str, Any]],
    slide_a: PptxSlide,
    slide_b: PptxSlide,
    object_a: PptxObject,
    object_b: PptxObject,
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
        if object_a.text != object_b.text:
            changes.append(
                _object_change(
                    "modified",
                    "text",
                    f"Text changed on slide {slide_a.index}: "
                    f"{object_a.text!r} -> {object_b.text!r}",
                    {"document": "both", "slide": slide_a.index},
                    object_a,
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
                )
            )
            changed_objects.append(_changed_object("formatting", slide_a.index, object_a, object_b))
    elif object_a.kind == "table":
        if object_a.table_cells != object_b.table_cells:
            changes.append(
                _object_change(
                    "modified",
                    "table",
                    f"Table changed on slide {slide_a.index}",
                    {"document": "both", "slide": slide_a.index},
                    object_a,
                )
            )
            changed_objects.append(_changed_object("table", slide_a.index, object_a, object_b))
    elif object_a.kind == "image":
        if object_a.image_sha256 != object_b.image_sha256:
            changes.append(
                _object_change(
                    "modified",
                    "image",
                    f"Image changed on slide {slide_a.index}",
                    {"document": "both", "slide": slide_a.index},
                    object_a,
                )
            )
            changed_objects.append(_changed_object("image", slide_a.index, object_a, object_b))
    elif object_a.shape_signature != object_b.shape_signature or object_a.text != object_b.text:
        changes.append(
            _object_change(
                "modified",
                "structure",
                f"Shape changed on slide {slide_a.index}",
                {"document": "both", "slide": slide_a.index},
                object_a,
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


def _object_change(
    change_type: str,
    category: str,
    message: str,
    source_ref: dict[str, Any],
    object_: PptxObject,
) -> dict[str, Any]:
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
            "page": source_ref["slide"],
            "x": round(left / 10_000_000, 4),
            "y": round(top / 10_000_000, 4),
            "width": round(width / 10_000_000, 4),
            "height": round(height / 10_000_000, 4),
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
