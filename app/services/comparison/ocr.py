from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

from PIL import Image


@dataclass(frozen=True)
class OcrToken:
    text: str
    confidence: float
    bbox: tuple[float, float, float, float]


@dataclass(frozen=True)
class OcrLine:
    text: str
    confidence: float
    tokens: list[OcrToken]


@dataclass(frozen=True)
class OcrBlock:
    text: str
    confidence: float
    lines: list[OcrLine]


@dataclass(frozen=True)
class OcrResult:
    text: str
    confidence: float
    blocks: list[OcrBlock]


class OcrEngine(Protocol):
    def extract(self, image: Image.Image) -> OcrResult: ...


class NoopOcrEngine:
    def extract(self, image: Image.Image) -> OcrResult:
        return OcrResult(text="", confidence=0.0, blocks=[])


class FakeOcrEngine:
    def __init__(self, text: str = "synthetic scan text", confidence: float = 0.95) -> None:
        self.text = text
        self.confidence = confidence

    def extract(self, image: Image.Image) -> OcrResult:
        token = OcrToken(text=self.text, confidence=self.confidence, bbox=(0.1, 0.1, 0.8, 0.1))
        line = OcrLine(text=self.text, confidence=self.confidence, tokens=[token])
        block = OcrBlock(text=self.text, confidence=self.confidence, lines=[line])
        return OcrResult(text=self.text, confidence=self.confidence, blocks=[block])


class TesseractOcrEngine:
    def __init__(self, language: str = "eng") -> None:
        self.language = language

    def extract(self, image: Image.Image) -> OcrResult:
        try:
            import pytesseract  # type: ignore[import-untyped]
        except ImportError:
            return OcrResult(text="", confidence=0.0, blocks=[])

        data = pytesseract.image_to_data(
            image,
            lang=self.language,
            output_type=pytesseract.Output.DICT,
        )
        tokens: list[OcrToken] = []
        width, height = image.size
        for index, text in enumerate(data.get("text", [])):
            cleaned = cleanup_text(text)
            if not cleaned:
                continue
            try:
                confidence = float(data["conf"][index]) / 100
            except (ValueError, TypeError):
                confidence = 0.0
            left = float(data["left"][index]) / width
            top = float(data["top"][index]) / height
            token_width = float(data["width"][index]) / width
            token_height = float(data["height"][index]) / height
            tokens.append(
                OcrToken(
                    text=cleaned,
                    confidence=confidence,
                    bbox=(left, top, token_width, token_height),
                )
            )
        return build_ocr_result(tokens)


class PaddleOcrEngine:
    def extract(self, image: Image.Image) -> OcrResult:
        try:
            from paddleocr import PaddleOCR  # type: ignore[import-not-found]
        except ImportError:
            return OcrResult(text="", confidence=0.0, blocks=[])

        engine = PaddleOCR(use_angle_cls=True, lang="en")
        result = engine.ocr(image, cls=True)
        tokens: list[OcrToken] = []
        width, height = image.size
        for line in result or []:
            for item in line or []:
                points, payload = item
                text, confidence = payload
                xs = [point[0] for point in points]
                ys = [point[1] for point in points]
                left = min(xs) / width
                top = min(ys) / height
                token_width = (max(xs) - min(xs)) / width
                token_height = (max(ys) - min(ys)) / height
                tokens.append(
                    OcrToken(
                        text=cleanup_text(str(text)),
                        confidence=float(confidence),
                        bbox=(left, top, token_width, token_height),
                    )
                )
        return build_ocr_result(tokens)


def get_ocr_engine(adapter: str, language: str = "eng") -> OcrEngine:
    if adapter == "fake":
        return FakeOcrEngine()
    if adapter == "tesseract":
        return TesseractOcrEngine(language=language)
    if adapter == "paddle":
        return PaddleOcrEngine()
    return NoopOcrEngine()


def filter_tokens(tokens: list[OcrToken], threshold: float) -> list[OcrToken]:
    return [token for token in tokens if token.confidence >= threshold and cleanup_text(token.text)]


def cleanup_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def build_ocr_result(tokens: list[OcrToken]) -> OcrResult:
    grouped_tokens = sorted(tokens, key=lambda token: (round(token.bbox[1], 2), token.bbox[0]))
    if not grouped_tokens:
        return OcrResult(text="", confidence=0.0, blocks=[])
    text = " ".join(token.text for token in grouped_tokens)
    confidence = sum(token.confidence for token in grouped_tokens) / len(grouped_tokens)
    line = OcrLine(text=text, confidence=confidence, tokens=grouped_tokens)
    block = OcrBlock(text=text, confidence=confidence, lines=[line])
    return OcrResult(text=text, confidence=confidence, blocks=[block])
