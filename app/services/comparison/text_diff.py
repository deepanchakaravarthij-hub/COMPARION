from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any


def token_changes(text_a: str, text_b: str) -> list[dict[str, Any]]:
    tokens_a = text_a.split()
    tokens_b = text_b.split()
    changes: list[dict[str, Any]] = []

    matcher = SequenceMatcher(a=tokens_a, b=tokens_b, autojunk=False)
    for tag, a_start, a_end, b_start, b_end in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "replace":
            message = (
                "Text modified: "
                f"{' '.join(tokens_a[a_start:a_end])!r} -> {' '.join(tokens_b[b_start:b_end])!r}"
            )
            change_type = "modified"
        elif tag == "delete":
            message = f"Text removed: {' '.join(tokens_a[a_start:a_end])!r}"
            change_type = "removed"
        else:
            message = f"Text added: {' '.join(tokens_b[b_start:b_end])!r}"
            change_type = "added"
        changes.append(
            {
                "type": change_type,
                "category": "text",
                "severity": "medium",
                "confidence": 0.9,
                "message": message,
                "source_ref": {"document": "both", "page": None},
            }
        )

    return changes
