from __future__ import annotations

import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

import fitz  # type: ignore[import-untyped]
from docx import Document  # type: ignore[import-untyped]


def docx_page_count(content: bytes) -> int:
    pdf_bytes = _convert_docx_to_pdf(content)
    with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
        return int(document.page_count)


def render_docx_page_png(content: bytes, page: int) -> bytes:
    if page < 1:
        raise ValueError("Page numbers are 1-based")
    pdf_bytes = _convert_docx_to_pdf(content)
    with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
        if page > document.page_count:
            raise ValueError("Page not found")
        pdf_page = document.load_page(page - 1)
        pixmap = pdf_page.get_pixmap(matrix=fitz.Matrix(1.75, 1.75), alpha=False)
        return bytes(pixmap.tobytes("png"))


def libreoffice_available() -> bool:
    return shutil.which("soffice") is not None


def _convert_docx_to_pdf(content: bytes) -> bytes:
    soffice = shutil.which("soffice")
    if not soffice:
        raise RuntimeError(
            "LibreOffice (soffice) is required to render DOCX page previews. "
            "Install LibreOffice or use the Docker image with libreoffice-writer."
        )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        docx_path = tmp_path / "document.docx"
        docx_path.write_bytes(content)
        subprocess.run(
            [
                soffice,
                "--headless",
                "--nologo",
                "--nofirststartwizard",
                "--convert-to",
                "pdf",
                "--outdir",
                str(tmp_path),
                str(docx_path),
            ],
            check=True,
            timeout=180,
            capture_output=True,
        )
        pdf_path = tmp_path / "document.pdf"
        if not pdf_path.exists():
            candidates = sorted(tmp_path.glob("*.pdf"))
            if not candidates:
                raise RuntimeError("LibreOffice did not produce a PDF export for the DOCX file")
            pdf_path = candidates[0]
        return pdf_path.read_bytes()


def estimate_page_count(content: bytes) -> int:
    try:
        return docx_page_count(content)
    except RuntimeError:
        document = Document(BytesIO(content))
        paragraphs = max(len(document.paragraphs), 1)
        return max(1, min(10, (paragraphs // 25) + 1))
