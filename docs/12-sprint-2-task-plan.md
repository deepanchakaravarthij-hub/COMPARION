# Sprint 2 Task Plan

## Sprint Goal

Reduce false positives for scanned documents and camera captures by adding OCR, preprocessing, orientation correction, deskewing, page alignment, debug artifacts, and scanned-document benchmark coverage.

## Current Baseline

Sprint 1 provides:
- Persisted job lifecycle using SQLite.
- Local artifact storage under `storage/`.
- PDF/image upload validation.
- PDF text extraction and rendering through PyMuPDF.
- Image normalization with Pillow.
- Baseline token diff and SSIM visual diff.
- Result JSON and HTML report endpoint.

Sprint 2 should extend the existing `app/services/comparison/` path rather than replacing it.

## In Scope

- OCR wrapper with a test-friendly fallback interface.
- Orientation detection and 90/180/270 degree correction.
- Deskewing using Hough or line-based angle estimation.
- Denoise, thresholding, and contrast enhancement options.
- OCR confidence filtering and text cleanup.
- OCR token grouping into lines, paragraphs, and blocks.
- Coarse page alignment for scale and orientation.
- ORB feature alignment with homography when enough features exist.
- Optional ECC fine alignment behind a feature flag.
- Alignment/debug artifacts stored per job.
- Scanned-document benchmark fixtures and regression tests.
- Benchmark metrics for runtime, false positives, and OCR confidence.

## Out of Scope

- Full perspective correction for arbitrary camera distortion.
- Handwriting OCR.
- Table-aware OCR structure.
- Semantic diffing or risk summaries.
- Frontend overlay viewer.
- Production OCR service deployment.

## Recommended Dependencies

- `opencv-python-headless` for deskewing, denoise, thresholding, ORB, homography, and ECC.
- `pytesseract` or a lightweight local OCR adapter for CI-friendly tests.
- `paddleocr` as the target production OCR adapter, optionally installed outside the default CI path if it is too heavy.
- `reportlab` or generated image fixtures for synthetic scanned PDFs, only if PyMuPDF-generated fixtures are not enough.

## Architecture Direction

Add these modules:
- `app/services/comparison/preprocessing.py`
- `app/services/comparison/ocr.py`
- `app/services/comparison/alignment.py`
- `app/services/comparison/debug_artifacts.py`
- `app/services/benchmarking.py`

Keep the existing `compare_service.py` as the pipeline coordinator. It should route PDF pages and image inputs through preprocessing and alignment before text/visual diffing.

## Workstream 1 - OCR Service Wrapper

### Tasks

- [ ] Define an `OcrEngine` protocol with `extract(image) -> OcrResult`.
- [ ] Add `OcrToken`, `OcrLine`, `OcrBlock`, and `OcrResult` models.
- [ ] Implement a deterministic fake OCR engine for tests.
- [ ] Implement a production adapter placeholder for PaddleOCR.
- [ ] Add settings for OCR enablement, confidence threshold, language, and adapter name.
- [ ] Add OCR confidence filtering.
- [ ] Add OCR text cleanup: whitespace normalization, punctuation cleanup, and low-confidence token removal.
- [ ] Group OCR tokens into lines and blocks by bounding-box proximity.

### Acceptance Checks

- [ ] OCR wrapper can be unit-tested without PaddleOCR installed.
- [ ] Low-confidence tokens are excluded from text diff.
- [ ] OCR output uses normalized coordinates.
- [ ] Result JSON can include OCR-derived source references.

## Workstream 2 - Preprocessing Pipeline

### Tasks

- [ ] Convert rendered PDF pages and image uploads into OpenCV-compatible arrays.
- [ ] Add grayscale normalization.
- [ ] Add denoise option using bilateral or median filtering.
- [ ] Add adaptive thresholding option.
- [ ] Add contrast enhancement option with CLAHE.
- [ ] Add orientation detection for 90/180/270 degree rotations.
- [ ] Add rotation correction.
- [ ] Add deskew angle estimation using Hough lines or min-area rectangle.
- [ ] Add deskew transform.
- [ ] Preserve preprocessing metadata in the comparison result.

### Acceptance Checks

- [ ] Rotated image fixture is corrected before diffing.
- [ ] Skewed image fixture is deskewed within a documented tolerance.
- [ ] Preprocessing can be disabled through settings for A/B benchmark comparison.
- [ ] Preprocessing metadata includes rotation angle, skew angle, and enabled operations.

## Workstream 3 - Page Alignment

### Tasks

- [ ] Add coarse alignment for size, page dimensions, and orientation.
- [ ] Add ORB feature detection and descriptor matching.
- [ ] Add homography estimation with RANSAC.
- [ ] Warp candidate image into reference page coordinates.
- [ ] Add match-count and reprojection-confidence thresholds.
- [ ] Add fallback path when feature matching is insufficient.
- [ ] Add optional ECC refinement behind a setting.
- [ ] Persist alignment matrix and confidence per page.

### Acceptance Checks

- [ ] Shifted/scaled scanned fixture aligns before visual diff.
- [ ] Low-feature pages fall back safely instead of failing the job.
- [ ] Alignment matrices are saved as debug JSON.
- [ ] Visual diff boxes are emitted in normalized post-alignment coordinates.

## Workstream 4 - Comparison Pipeline Integration

### Tasks

- [ ] Update PDF pipeline to preprocess rendered pages before visual comparison.
- [ ] Update image pipeline to preprocess uploaded images before visual comparison.
- [ ] Use OCR text when native PDF text is empty or low quality.
- [ ] Compare OCR text blocks when scan mode is active.
- [ ] Add change categories for `ocr`, `alignment`, and `preprocessing` diagnostics if needed.
- [ ] Add confidence composition from OCR, alignment, and visual diff confidence.
- [ ] Include preprocessing and alignment metadata in result JSON without breaking schema versioning.
- [ ] Bump result schema version if response shape changes.

### Acceptance Checks

- [ ] Native PDF text path still works for digital PDFs.
- [ ] Scanned PDF path can produce text changes via OCR.
- [ ] Existing Sprint 1 tests remain green.
- [ ] Result ordering remains deterministic.

## Workstream 5 - Debug Artifacts

### Tasks

- [ ] Store preprocessed page images for failed or low-confidence cases.
- [ ] Store alignment matrices as JSON.
- [ ] Store before/after thumbnails for orientation and deskew operations.
- [ ] Add artifact paths to job metadata or result diagnostics.
- [ ] Avoid storing document text in logs.

### Acceptance Checks

- [ ] Debug artifacts are saved under job-scoped storage paths.
- [ ] Failed alignment cases include useful diagnostics.
- [ ] Artifacts are not exposed through public API unless explicitly linked.

## Workstream 6 - Benchmarks and Tests

### Tasks

- [ ] Add generated fixtures for rotated, skewed, noisy, low-contrast, and shifted scanned inputs.
- [ ] Add unit tests for orientation detection.
- [ ] Add unit tests for deskew angle estimation.
- [ ] Add unit tests for OCR confidence filtering and grouping.
- [ ] Add unit tests for ORB alignment fallback behavior.
- [ ] Add API integration test for scanned PDF/image comparison.
- [ ] Add benchmark runner that records runtime and change counts.
- [ ] Add benchmark output format under `benchmarks/expected/`.

### Acceptance Checks

- [ ] Regression tests pass for rotated and skewed fixtures.
- [ ] Benchmark report records Sprint 1 baseline vs Sprint 2 preprocessing-enabled output.
- [ ] False-positive count decreases for at least one scanned fixture class.
- [ ] Runtime impact is recorded per page/image.

## Suggested Implementation Order

1. Add OpenCV dependency and preprocessing module with generated fixture tests.
2. Add orientation correction and deskew tests.
3. Add OCR models, fake OCR engine, and confidence filtering.
4. Integrate OCR fallback when PDF native text is empty.
5. Add coarse alignment and ORB homography.
6. Add debug artifact writer and alignment metadata.
7. Integrate preprocessing/alignment into PDF and image comparison.
8. Add scanned benchmark fixtures and benchmark runner.
9. Update result schema/docs and Sprint 2 checklist.
10. Run full verification and compare Sprint 1 vs Sprint 2 benchmark output.

## Risks and Mitigations

- **PaddleOCR is heavy for CI.** Use an adapter interface and fake OCR in tests; keep PaddleOCR optional until runtime packaging is ready.
- **OpenCV alignment may be unstable on low-text pages.** Require match-count thresholds and safe fallback to Sprint 1 visual diff.
- **Preprocessing can hide real visual changes.** Keep preprocessing metadata and configurable toggles for benchmark comparison.
- **Synthetic fixtures may be too clean.** Start synthetic for CI, then add curated real-world non-confidential scans later.
- **Result schema growth can become messy.** Add diagnostics as structured optional metadata and bump schema version only when response contracts change.

## Demo Script

1. Upload two scanned images where one is rotated.
2. Show job result with orientation correction metadata.
3. Upload a skewed scanned image pair.
4. Show deskew/alignment diagnostics and reduced visual noise.
5. Upload a scanned PDF with no native text.
6. Show OCR-derived text changes in result JSON.
7. Open the HTML report and confirm changes remain readable.

## Sprint 2 Definition of Done

- [x] OCR wrapper and test adapter are implemented.
- [x] Preprocessing pipeline supports orientation correction, deskew, denoise, thresholding, and contrast enhancement.
- [x] Page alignment supports coarse alignment and ORB/homography fallback behavior.
- [x] OCR fallback works for scanned PDFs/images when an OCR adapter is configured.
- [x] Debug artifacts are persisted for low-confidence or failed alignment cases.
- [x] Scanned benchmark fixtures and regression tests are committed.
- [x] Benchmark output records false-positive and runtime impact.
- [x] Sprint 1 tests remain green.
- [x] Sprint 2 checklist in `sprint_plan.md` is updated.
