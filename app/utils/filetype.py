from pathlib import Path

_EXT_TO_TYPE = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".xlsx": "xlsx",
    ".ppt": "ppt",
    ".pptx": "pptx",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".tif": "image",
    ".tiff": "image",
    ".bmp": "image",
    ".webp": "image",
}


def detect_type(filename: str) -> str:
    return _EXT_TO_TYPE.get(Path(filename).suffix.lower(), "unknown")
