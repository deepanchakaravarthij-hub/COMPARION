from typing import Any

from app.utils.filetype import detect_type


def compare_files(
    file_a_name: str,
    file_b_name: str,
    content_a: bytes,
    content_b: bytes,
) -> dict[str, Any]:
    type_a = detect_type(file_a_name)
    type_b = detect_type(file_b_name)

    if type_a != type_b:
        return {
            "summary": "File types differ; comparison is limited",
            "file_type": f"{type_a} vs {type_b}",
            "changes": [{"type": "warning", "message": "Different file types uploaded"}],
        }

    if content_a == content_b:
        return {
            "summary": "No differences detected (binary match)",
            "file_type": type_a,
            "changes": [],
        }

    return {
        "summary": "Differences detected (POC baseline comparator)",
        "file_type": type_a,
        "changes": [
            {
                "type": "modified",
                "message": "Binary content differs; advanced per-format diff pending",
            }
        ],
    }
