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

- [ ] Integrate PaddleOCR service wrapper.
- [ ] Add orientation detection and rotation correction.
- [ ] Add deskew pipeline using Hough or line-based methods.
- [ ] Add denoise, thresholding, and contrast enhancement options.
- [ ] Add OCR confidence filtering.
- [ ] Add OCR token cleanup and normalization.
- [ ] Group OCR tokens into lines, paragraphs, and blocks.

### Alignment

- [ ] Implement coarse page alignment for scale and orientation.
- [ ] Implement feature-based alignment with ORB and homography.
- [ ] Add optional fine alignment refinement with ECC.
- [ ] Persist alignment matrices for debug and replay.
- [ ] Emit visual debug artifacts for failed or low-confidence alignments.

### QA and Benchmarking

- [ ] Build scanned-document benchmark set with rotated, skewed, noisy, and low-resolution examples.
- [ ] Track precision, recall, and false-positive rate.
- [ ] Add regression tests for rotated and skewed scanned cases.

### Exit Criteria

- [ ] Rotated and skewed scan cases complete successfully.
- [ ] False-positive rate improves against the Sprint 1 baseline.
- [ ] Alignment failures are visible in logs and report diagnostics.

---

## Sprint 3 - DOCX Structural Comparison

**Goal:** Detect Word-level textual and structural changes.

### Parser and Model

- [ ] Implement DOCX parser for paragraphs, runs, tables, headers, footers, and embedded images.
- [ ] Extract style metadata: font, size, emphasis, alignment, color, and numbering.
- [ ] Map DOCX content into the Unified Document Model.
- [ ] Preserve stable source references for report navigation.

### Diffing

- [ ] Add paragraph-level and run-level text diff.
- [ ] Add formatting diff classifier.
- [ ] Add table structural diff for rows, columns, and cell values.
- [ ] Add reorder and move detection heuristics for sections and paragraphs.

### Reporting

- [ ] Add DOCX-specific change categories in JSON.
- [ ] Render DOCX changes in the HTML report.
- [ ] Add confidence and severity scoring for each DOCX change.

### Exit Criteria

- [ ] DOCX changes are grouped by text, formatting, table, image, and structure.
- [ ] Report output is stable across repeated runs for the same fixture pair.

---

## Sprint 4 - XLSX Comparison Engine

**Goal:** Add spreadsheet-aware comparison with cell and formula intelligence.

### Parser and Diff

- [ ] Implement workbook and sheet parser with `openpyxl`.
- [ ] Detect sheet add, remove, rename, and reorder events.
- [ ] Add cell-level value diff.
- [ ] Add formula diff with normalized formula parsing.
- [ ] Add row and column insertion/deletion detection.
- [ ] Add style and format diff with configurable thresholding.
- [ ] Detect hidden rows, columns, and sheet metadata changes.

### Reporting

- [ ] Add sheet-level summary.
- [ ] Add drill-down view for changed cells.
- [ ] Export machine-readable changed-cell list.

### Exit Criteria

- [ ] XLSX comparison supports multi-sheet workbooks.
- [ ] Formula and value changes are clearly separated in output.

---

## Sprint 5 - PPTX Comparison Engine

**Goal:** Add slide-aware object-level comparison.

### Parsing

- [ ] Implement PPTX object extraction for text boxes, shapes, tables, and images.
- [ ] Add slide rendering pipeline for visual diff overlays.
- [ ] Add slide mapping and reorder detection.
- [ ] Capture object-level coordinates for report overlays.

### Diffing

- [ ] Add text box text diff.
- [ ] Add text style diff.
- [ ] Add shape and table object diff.
- [ ] Add embedded image diff using hash and SSIM hooks.

### Reporting

- [ ] Add slide-level summary.
- [ ] Add object-level change list.
- [ ] Render slide visual overlays in HTML report.

### Exit Criteria

- [ ] PPTX reports slide-level and object-level modifications.
- [ ] Slide reorder and object changes are distinguishable.

---

## Sprint 6 - Unified Model, API Hardening, and Frontend Viewer

**Goal:** Stabilize one cross-format contract and deliver an operator-friendly UI.

### Unified Model and API

- [ ] Finalize UDM schema and validation contracts.
- [ ] Add backward-compatible API response versioning.
- [ ] Add pagination and filtering for large result sets.
- [ ] Add signed report download URLs when object storage is enabled.
- [ ] Add API documentation examples for every supported format.

### Frontend

- [ ] Build upload and compare job submission UI.
- [ ] Build job status polling and history list.
- [ ] Build side-by-side viewer with overlay boxes.
- [ ] Add change list sidebar with filters for type, severity, page, slide, and sheet.
- [ ] Add synchronized navigation across compared documents.
- [ ] Add report download action.

### Exit Criteria

- [ ] Stakeholder demo flow is functional end to end.
- [ ] Same UI can inspect PDF/image, DOCX, XLSX, and PPTX result categories.

---

## Sprint 7 - Semantic Layer and Risk Summaries

**Goal:** Reduce noise and provide business-meaningful change insights.

### Semantic Intelligence

- [ ] Integrate embedding model service such as BGE, Jina, or GTE.
- [ ] Add semantic similarity scoring for changed blocks.
- [ ] Label changes as wording-only, meaning-changed, moved, or reordered.
- [ ] Add semantic matching across sections and pages.

### AI Summaries

- [ ] Create prompt templates for change summary and risk explanation.
- [ ] Add high-risk rule templates for finance, legal, and compliance documents.
- [ ] Add optional local LLM summarization pipeline.
- [ ] Store summary provenance and confidence metadata.

### Exit Criteria

- [ ] Reports include semantic summary, risk summary, and confidence.
- [ ] Semantic labels reduce repeated or noisy low-value changes in benchmark reports.

---

## Sprint 8 - Production Readiness and Pilot Hardening

**Goal:** Make the system reliable, observable, and scalable enough for pilot usage.

### Reliability and Operations

- [ ] Move background work to Celery workers.
- [ ] Add retry policy and dead-letter queue.
- [ ] Add idempotency keys for compare jobs.
- [ ] Add audit logs for job lifecycle and report access.
- [ ] Add monitoring dashboards for latency, failures, queue depth, and worker health.
- [ ] Add alerting for worker failures and SLA breaches.

### Security

- [ ] Add authentication and authorization using JWT or API keys.
- [ ] Add file sanitization and malware scan hook.
- [ ] Add PII-safe logging policy.
- [ ] Add retention and deletion policy for uploaded documents and reports.

### Performance

- [ ] Build load test scenarios for small, medium, and large documents.
- [ ] Profile OCR, alignment, rendering, and report generation bottlenecks.
- [ ] Add caching and batching where benchmark data shows value.
- [ ] Document pilot deployment sizing assumptions.

### Exit Criteria

- [ ] Pilot-ready deployment has SLA, observability, security, and recovery baseline.
- [ ] Load test results and known limits are documented.

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
- [ ] Sprint 2 complete.
- [ ] Sprint 3 complete.
- [ ] Sprint 4 complete.
- [ ] Sprint 5 complete.
- [ ] Sprint 6 complete.
- [ ] Sprint 7 complete.
- [ ] Sprint 8 complete.
- [ ] Program acceptance criteria met.
- [ ] Stakeholder demo signed off.
- [ ] Pilot rollout readiness review passed.
