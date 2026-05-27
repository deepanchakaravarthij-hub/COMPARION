from __future__ import annotations

from unittest.mock import MagicMock, patch

from PIL import Image

from app.services.comparison.ocr import (
    EasyOcrEngine,
    _split_detection_tokens,
    get_ocr_engine,
)


def test_get_ocr_engine_easyocr_adapter() -> None:
    engine = get_ocr_engine("easyocr", "en")
    assert isinstance(engine, EasyOcrEngine)


def test_split_detection_tokens_splits_phrases() -> None:
    tokens = _split_detection_tokens("147 average", (0.1, 0.2, 0.2, 0.03), confidence=0.9)
    assert len(tokens) == 2
    assert tokens[0].text == "147"
    assert tokens[1].text == "average"


@patch("app.services.comparison.ocr._get_easyocr_reader")
def test_easyocr_engine_maps_detections(mock_reader: MagicMock) -> None:
    mock_reader.return_value.readtext.return_value = [
        ([[10, 20], [50, 20], [50, 40], [10, 40]], "149 average", 0.92),
    ]
    image = Image.new("RGB", (100, 100), "white")
    result = EasyOcrEngine(language="en").extract(image)
    assert result.text
    assert len(result.blocks[0].lines[0].tokens) >= 2
