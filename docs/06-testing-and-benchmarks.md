# Testing and Benchmarks

## Test levels
- Unit tests per comparator.
- Golden regression tests with fixtures.
- End-to-end API+worker tests.

## Metrics
- Precision/recall for change detection.
- False positive rate.
- Runtime per page/slide/sheet.
- OCR confidence distributions.

## Sprint 2 Scan Benchmark Cases

- Rotated scanned image: candidate is rotated 90 degrees and should be corrected to portrait orientation.
- Skewed scanned image: skew angle should be detected and reduced before visual diffing.
- Shifted scanned image: alignment should return diagnostics and keep output coordinates normalized.
- Empty-native-text PDF: OCR fallback should provide text when an OCR adapter is configured.

Expected outputs live under `benchmarks/expected/`.
