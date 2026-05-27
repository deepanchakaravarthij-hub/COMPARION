from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Protocol

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
            config="--psm 6",
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


def _bbox_from_points(
    points: list[list[float]],
    width: int,
    height: int,
) -> tuple[float, float, float, float]:
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    left = min(xs) / width
    top = min(ys) / height
    token_width = (max(xs) - min(xs)) / width
    token_height = (max(ys) - min(ys)) / height
    return left, top, token_width, token_height


def _split_detection_tokens(
    text: str,
    bbox: tuple[float, float, float, float],
    confidence: float = 1.0,
) -> list[OcrToken]:
    words = [cleanup_text(word) for word in text.split()]
    words = [word for word in words if word]
    if not words:
        return []
    if len(words) == 1:
        return [OcrToken(text=words[0], confidence=confidence, bbox=bbox)]

    left, top, token_width, token_height = bbox
    slice_width = token_width / len(words)
    return [
        OcrToken(
            text=word,
            confidence=confidence,
            bbox=(left + index * slice_width, top, slice_width, token_height),
        )
        for index, word in enumerate(words)
    ]


@lru_cache(maxsize=4)
def _get_easyocr_reader(language_key: str) -> Any:
    import easyocr  # type: ignore[import-not-found]

    languages = [item.strip() for item in language_key.split(",") if item.strip()]
    return easyocr.Reader(languages, gpu=False, verbose=False)


class EasyOcrEngine:
    """EasyOCR adapter — strong on UI screenshots and colored dashboard text."""

    def __init__(self, language: str = "en") -> None:
        self.languages = _easyocr_languages(language)

    def extract(self, image: Image.Image) -> OcrResult:
        try:
            import numpy as np
        except ImportError:
            return OcrResult(text="", confidence=0.0, blocks=[])

        try:
            reader = _get_easyocr_reader(",".join(self.languages))
        except Exception:
            return OcrResult(text="", confidence=0.0, blocks=[])

        if image.mode != "RGB":
            image = image.convert("RGB")

        width, height = image.size
        detections = reader.readtext(np.array(image), detail=1, paragraph=False)
        tokens: list[OcrToken] = []
        for item in detections:
            if len(item) != 3:
                continue
            points, text, confidence = item
            cleaned = cleanup_text(str(text))
            if not cleaned:
                continue
            bbox = _bbox_from_points(points, width, height)
            for token in _split_detection_tokens(cleaned, bbox, confidence=float(confidence)):
                tokens.append(token)
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
    if adapter == "easyocr":
        return EasyOcrEngine(language=language)
    if adapter == "tesseract":
        return TesseractOcrEngine(language=_tesseract_language(language))
    if adapter == "paddle":
        return PaddleOcrEngine()
    if adapter == "none":
        if _easyocr_available():
            return EasyOcrEngine(language=language)
        if _tesseract_available():
            return TesseractOcrEngine(language=_tesseract_language(language))
        return NoopOcrEngine()
    return NoopOcrEngine()


def _easyocr_available() -> bool:
    try:
        import easyocr  # type: ignore[import-not-found]  # noqa: F401

        return True
    except Exception:
        return False


def _tesseract_available() -> bool:
    try:
        import pytesseract  # type: ignore[import-untyped]

        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


def _easyocr_languages(language: str) -> list[str]:
    if language in {"en", "eng", "english"}:
        return ["en"]
    if "," in language:
        return [item.strip() for item in language.split(",") if item.strip()]
    return [language]


def _tesseract_language(language: str) -> str:
    if language in {"en", "eng"}:
        return "eng"
    return language


def _reading_order_tokens(tokens: list[OcrToken]) -> list[OcrToken]:
    if not tokens:
        return []
    sorted_tokens = sorted(tokens, key=lambda token: (token.bbox[1], token.bbox[0]))
    lines: list[list[OcrToken]] = []
    for token in sorted_tokens:
        if not lines or abs(token.bbox[1] - lines[-1][0].bbox[1]) > 0.015:
            lines.append([token])
        else:
            lines[-1].append(token)
    ordered: list[OcrToken] = []
    for line in lines:
        ordered.extend(sorted(line, key=lambda token: token.bbox[0]))
    return ordered


def extract_ocr_words(
    image: Image.Image,
    *,
    confidence_threshold: float = 0.6,
    adapter: str,
    language: str = "en",
    enabled: bool = True,
) -> tuple[list[dict[str, float | str]], float]:
    if not enabled:
        return [], 0.0
    if image.mode not in {"RGB", "L"} or image.mode == "L":
        image = image.convert("RGB")

    width, height = image.size
    max_dimension = max(width, height)
    if max_dimension < 2400:
        scale = min(2.0, 2400 / max_dimension)
        if scale > 1.05:
            image = image.resize(
                (int(width * scale), int(height * scale)),
                Image.Resampling.LANCZOS,
            )

    engine = get_ocr_engine(adapter, language)
    result = engine.extract(image)
    tokens = [token for block in result.blocks for line in block.lines for token in line.tokens]
    filtered = filter_tokens(tokens, confidence_threshold)
    ordered = _reading_order_tokens(filtered)
    if not ordered:
        return [], result.confidence

    words: list[dict[str, float | str]] = []
    for token in ordered:
        left, top, width, height = token.bbox
        pad_x = max(0.001, width * 0.08)
        pad_y = max(0.001, height * 0.12)
        words.append(
            {
                "text": token.text,
                "x": max(0.0, left - pad_x),
                "y": max(0.0, top - pad_y),
                "w": min(1.0 - left, width + (pad_x * 2)),
                "h": min(1.0 - top, height + (pad_y * 2)),
            }
        )
    confidence = sum(token.confidence for token in ordered) / len(ordered)
    return words, round(confidence, 3)


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
