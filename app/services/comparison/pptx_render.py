from __future__ import annotations

import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

import fitz  # type: ignore[import-untyped]
from pptx import Presentation  # type: ignore[import-untyped]


def pptx_slide_count(content: bytes) -> int:
    presentation = Presentation(BytesIO(content))
    return len(presentation.slides)


def render_pptx_slide_png(content: bytes, slide: int) -> bytes:
    if slide < 1:
        raise ValueError("Slide numbers are 1-based")
    pdf_bytes = _convert_pptx_to_pdf(content)
    with fitz.open(stream=pdf_bytes, filetype="pdf") as document:
        if slide > document.page_count:
            raise ValueError("Slide not found")
        page = document.load_page(slide - 1)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(1.75, 1.75), alpha=False)
        return bytes(pixmap.tobytes("png"))


def libreoffice_available() -> bool:
    return shutil.which("soffice") is not None


def _convert_pptx_to_pdf(content: bytes) -> bytes:
    soffice = shutil.which("soffice")
    if not soffice:
        raise RuntimeError(
            "LibreOffice (soffice) is required to render PPTX slide previews. "
            "Install LibreOffice or use the Docker image with libreoffice-impress."
        )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        pptx_path = tmp_path / "deck.pptx"
        pptx_path.write_bytes(content)
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
                str(pptx_path),
            ],
            check=True,
            timeout=180,
            capture_output=True,
        )
        pdf_path = tmp_path / "deck.pdf"
        if not pdf_path.exists():
            candidates = sorted(tmp_path.glob("*.pdf"))
            if not candidates:
                raise RuntimeError("LibreOffice did not produce a PDF export for the PPTX file")
            pdf_path = candidates[0]
        return pdf_path.read_bytes()
