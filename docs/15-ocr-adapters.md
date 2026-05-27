# OCR adapters

COMPARION routes scanned PDF pages and image uploads through `extract_ocr_words` in `app/services/comparison/ocr.py`.

## Adapter selection

| Adapter | Env value | Strengths | Notes |
|---------|-----------|-----------|-------|
| EasyOCR | `easyocr` | UI text, colored dashboards, GPU | Default in `.env.example`; set `COMPARION_OCR_USE_GPU=1` with NVIDIA runtime |
| Tesseract | `tesseract` | Clean printed scans, low footprint | Requires `tesseract-ocr` system package |
| PaddleOCR | `paddle` | Rotation + multilingual scans | Optional dependency; heavier install |
| Auto | `none` | Picks EasyOCR then Tesseract when available | Used when adapter is unset |

## Related scan settings

- `COMPARION_SCAN_WORD_THRESHOLD` — native PDF words below this count trigger OCR on that page.
- `COMPARION_SCAN_FORCE_OCR=1` — OCR every PDF page regardless of native text.
- `COMPARION_PDF_SUPPLEMENT_VISUAL=1` — pixel diff for figures/signatures with text-region masking.
- `COMPARION_OCR_CONFIDENCE_THRESHOLD` — drop low-confidence tokens before diff.

## Layout models (future)

`COMPARION_LAYOUT_ADAPTER` is reserved for Paddle PP-Structure or similar figure/text segmentation. Not enabled in the current POC.
