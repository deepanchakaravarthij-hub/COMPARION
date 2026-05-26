# COMPARION Detailed Sprint Plan

This plan breaks the COMPARION document comparison POC into execution-ready sprints with clear scope, checklist items, deliverables, and acceptance gates.

## Current Repository Baseline

- FastAPI application scaffold exists.
- Current endpoints: `GET /health`, `POST /v1/compare`, `GET /v1/jobs/{job_id}`, `GET /v1/jobs/{job_id}/result`.
- Current job storage is in-memory.
- Current comparator is a baseline binary comparator.
- Documentation set exists under `docs/`.

## POC Objective

Ship a production-like POC that compares two versions of supported documents and produces deterministic structured JSON plus an operator-friendly HTML report.

Supported target formats:
- PDF
- Images and scanned documents
- DOCX
- XLSX
- PPTX

Core capabilities:
- Textual differences
- Structural differences
- Visual differences with coordinates and overlays
- OCR normalization for scans, rotation, skew, and noisy captures
- Unified Document Model (UDM)
- Confidence and severity scoring
- Optional semantic and risk summaries

## Assumptions

- Sprint length: 2 weeks unless noted.
- Team: 3-5 engineers across backend, CV/OCR, frontend, QA, and DevOps.
- POC target: pilot-quality system, not full enterprise platform.
- Primary benchmark target: curated dataset with representative clean, scanned, rotated, skewed, and noisy documents.

## Program Acceptance Criteria

- Compare two same-type documents and return stable JSON plus HTML report.
- Highlight added, removed, and modified content with page, slide, sheet, cell, or normalized coordinate references.
- Handle rotated and skewed scanned inputs with stable overlays.
- Keep false-positive rate at or below 10% on the curated benchmark set.
- Persist job lifecycle and failure reasons.
- Provide repeatable tests and benchmark output for each major engine path.

---

## Sprint 0 - Foundation and Delivery Workflow

**Goal:** Make the existing scaffold reliable for team development and CI.

### Checklist

- [x] Confirm POC scope and classify features as must-have, should-have, and later.
- [x] Define non-functional targets: latency, max file size, throughput, false-positive rate, and retention.
- [x] Create Architecture Decision Records for core choices.
- [x] Add repository standards: branch rules, commit conventions, PR template, and issue template.
- [x] Add Python tooling: `ruff`, `black`, `mypy`, and `pre-commit`.
- [x] Add baseline CI for linting and tests.
- [x] Add Docker Compose for FastAPI, Redis, Postgres, and MinIO.
- [x] Add centralized config management with `.env` and a settings module.
- [x] Add structured logging with request IDs and job correlation IDs.
- [x] Create benchmark fixture folder structure and naming rules.
- [x] Document local setup in `README.md`.

### Deliverables

- Repeatable local development setup.
- CI pipeline running on each pull request.
- Benchmark fixture structure checked into the repository.

### Exit Criteria

- [x] New contributor can run the project locally in 30 minutes or less.
- [x] CI must pass before merge.
- [x] Health endpoint and current API tests pass locally and in CI.

---

## Sprint 1 - Persistent Job Workflow and PDF/Image Baseline

**Goal:** Upgrade the current scaffold into an end-to-end PDF/image comparison workflow with persisted job metadata.

### Backend and API

- [x] Replace in-memory job store with DB-backed job table.
- [x] Add job states: `queued`, `running`, `completed`, `failed`, `cancelled`.
- [x] Add upload validation for size, MIME type, extension, and duplicate uploads.
- [x] Save uploaded files through a storage abstraction that supports local disk and MinIO.
- [x] Add result schema versioning with `result_schema_version`.
- [x] Add consistent API error contract.
- [x] Add basic retry behavior for transient processing failures.
- [x] Add report download endpoint.

### Comparison Engine

- [x] Implement file-type routing pipeline.
- [x] Add PDF page rendering with PyMuPDF.
- [x] Add image normalization path: resize, grayscale, thresholding, and optional denoise.
- [x] Add native PDF text extraction where available.
- [x] Add baseline text diff using token-level comparison.
- [x] Add baseline visual diff using SSIM and contour bounding boxes.
- [x] Emit normalized JSON with page-level coordinates.
- [x] Generate HTML report stub with summary and page-level changes.

### QA

- [x] Add unit tests for job state transitions.
- [x] Add API integration tests for uploads, status polling, result retrieval, and error paths.
- [x] Add golden tests for simple PDF and image fixtures.

### Exit Criteria

- [x] User can upload two PDFs or images and receive deterministic JSON plus an HTML report.
- [x] Failed jobs include a clear machine-readable and human-readable reason.
- [x] Simple PDF/image benchmark cases run in CI.

---

## Sprint 2 - Scanned Document Robustness

**Goal:** Reduce false positives for scanned documents and camera captures.

### OCR and Preprocessing

- [x] Integrate PaddleOCR service wrapper.
- [x] Add orientation detection and rotation correction.
- [x] Add deskew pipeline using Hough or line-based methods.
- [x] Add denoise, thresholding, and contrast enhancement options.
- [x] Add OCR confidence filtering.
- [x] Add OCR token cleanup and normalization.
- [x] Group OCR tokens into lines, paragraphs, and blocks.

### Alignment

- [x] Implement coarse page alignment for scale and orientation.
- [x] Implement feature-based alignment with ORB and homography.
- [x] Add optional fine alignment refinement with ECC.
- [x] Persist alignment matrices for debug and replay.
- [x] Emit visual debug artifacts for failed or low-confidence alignments.

### QA and Benchmarking

- [x] Build scanned-document benchmark set with rotated, skewed, noisy, and low-resolution examples.
- [x] Track precision, recall, and false-positive rate.
- [x] Add regression tests for rotated and skewed scanned cases.

### Exit Criteria

- [x] Rotated and skewed scan cases complete successfully.
- [x] False-positive rate improves against the Sprint 1 baseline.
- [x] Alignment failures are visible in logs and report diagnostics.

---

## Sprint 3 - DOCX Structural Comparison

**Goal:** Detect Word-level textual and structural changes.

### Parser and Model

- [x] Implement DOCX parser for paragraphs, runs, tables, headers, footers, and embedded images.
- [x] Extract style metadata: font, size, emphasis, alignment, color, and numbering.
- [x] Map DOCX content into the Unified Document Model.
- [x] Preserve stable source references for report navigation.

### Diffing

- [x] Add paragraph-level and run-level text diff.
- [x] Add formatting diff classifier.
- [x] Add table structural diff for rows, columns, and cell values.
- [x] Add reorder and move detection heuristics for sections and paragraphs.

### Reporting

- [x] Add DOCX-specific change categories in JSON.
- [x] Render DOCX changes in the HTML report.
- [x] Add confidence and severity scoring for each DOCX change.

### Exit Criteria

- [x] DOCX changes are grouped by text, formatting, table, image, and structure.
- [x] Report output is stable across repeated runs for the same fixture pair.

---

## Sprint 4 - XLSX Comparison Engine

**Goal:** Add spreadsheet-aware comparison with cell and formula intelligence.

### Parser and Diff

- [x] Implement workbook and sheet parser with `openpyxl`.
- [x] Detect sheet add, remove, rename, and reorder events.
- [x] Add cell-level value diff.
- [x] Add formula diff with normalized formula parsing.
- [x] Add row and column insertion/deletion detection.
- [x] Add style and format diff with configurable thresholding.
- [x] Detect hidden rows, columns, and sheet metadata changes.

### Reporting

- [x] Add sheet-level summary.
- [x] Add drill-down view for changed cells.
- [x] Export machine-readable changed-cell list.

### Exit Criteria

- [x] XLSX comparison supports multi-sheet workbooks.
- [x] Formula and value changes are clearly separated in output.

---

## Sprint 5 - PPTX Comparison Engine

**Goal:** Add slide-aware object-level comparison.

### Parsing

- [x] Implement PPTX object extraction for text boxes, shapes, tables, and images.
- [x] Add slide rendering pipeline for visual diff overlays.
- [x] Add slide mapping and reorder detection.
- [x] Capture object-level coordinates for report overlays.

### Diffing

- [x] Add text box text diff.
- [x] Add text style diff.
- [x] Add shape and table object diff.
- [x] Add embedded image diff using hash and SSIM hooks.

### Reporting

- [x] Add slide-level summary.
- [x] Add object-level change list.
- [x] Render slide visual overlays in HTML report.

### Exit Criteria

- [x] PPTX reports slide-level and object-level modifications.
- [x] Slide reorder and object changes are distinguishable.

---

## Sprint 6 - Unified Model, API Hardening, and Frontend Viewer

**Goal:** Stabilize one cross-format contract and deliver an operator-friendly UI.

### Unified Model and API

- [x] Finalize UDM schema and validation contracts.
- [x] Add backward-compatible API response versioning.
- [x] Add pagination and filtering for large result sets.
- [x] Add signed report download URLs when object storage is enabled.
- [x] Add API documentation examples for every supported format.

### Frontend

- [x] Build upload and compare job submission UI.
- [x] Build job status polling and history list.
- [x] Build side-by-side viewer with overlay boxes.
- [x] Add change list sidebar with filters for type, severity, page, slide, and sheet.
- [x] Add synchronized navigation across compared documents.
- [x] Add report download action.

### Exit Criteria

- [x] Stakeholder demo flow is functional end to end.
- [x] Same UI can inspect PDF/image, DOCX, XLSX, and PPTX result categories.

---

## Sprint 7 - Semantic Layer and Risk Summaries

**Goal:** Reduce noise and provide business-meaningful change insights.

### Semantic Intelligence

- [x] Integrate embedding model service such as BGE, Jina, or GTE.
- [x] Add semantic similarity scoring for changed blocks.
- [x] Label changes as wording-only, meaning-changed, moved, or reordered.
- [x] Add semantic matching across sections and pages.

### AI Summaries

- [x] Create prompt templates for change summary and risk explanation.
- [x] Add high-risk rule templates for finance, legal, and compliance documents.
- [x] Add optional local LLM summarization pipeline.
- [x] Store summary provenance and confidence metadata.

### Exit Criteria

- [x] Reports include semantic summary, risk summary, and confidence.
- [x] Semantic labels reduce repeated or noisy low-value changes in benchmark reports.

---

## Sprint 8 - Production Readiness and Pilot Hardening

**Goal:** Make the system reliable, observable, and scalable enough for pilot usage.

### Reliability and Operations

- [x] Move background work to Celery workers.
- [x] Add retry policy and dead-letter queue.
- [x] Add idempotency keys for compare jobs.
- [x] Add audit logs for job lifecycle and report access.
- [x] Add monitoring dashboards for latency, failures, queue depth, and worker health.
- [x] Add alerting for worker failures and SLA breaches.

### Security

- [x] Add authentication and authorization using JWT or API keys.
- [x] Add file sanitization and malware scan hook.
- [x] Add PII-safe logging policy.
- [x] Add retention and deletion policy for uploaded documents and reports.

### Performance

- [x] Build load test scenarios for small, medium, and large documents.
- [x] Profile OCR, alignment, rendering, and report generation bottlenecks.
- [x] Add caching and batching where benchmark data shows value.
- [x] Document pilot deployment sizing assumptions.

### Exit Criteria

- [x] Pilot-ready deployment has SLA, observability, security, and recovery baseline.
- [x] Load test results and known limits are documented.

---

## Cross-Sprint Definition of Done

Every story or task should satisfy the following before being marked done:

- [ ] Code implemented and reviewed.
- [ ] Unit tests added or updated.
- [ ] Integration tests added or updated where API or workflow behavior changes.
- [ ] Documentation updated when API, architecture, data model, or operations behavior changes.
- [ ] Structured logging and error handling included.
- [ ] Benchmark impact recorded when a diff engine or normalization path changes.
- [ ] Security and privacy checklist passed.

---

## Master Tracking Checklist

- [x] Sprint 0 complete.
- [x] Sprint 1 complete.
- [x] Sprint 2 complete.
- [x] Sprint 3 complete.
- [x] Sprint 4 complete.
- [x] Sprint 5 complete.
- [x] Sprint 6 complete.
- [x] Sprint 7 complete.
- [x] Sprint 8 complete.
- [ ] Program acceptance criteria met.
- [ ] Stakeholder demo signed off.
- [ ] Pilot rollout readiness review passed.
