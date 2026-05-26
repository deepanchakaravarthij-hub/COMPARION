# COMPARION Detailed Sprint Plan (Task Checklist)

This plan breaks the project into execution-ready sprints with clear checklists, ownership targets, and exit criteria.

## Assumptions
- Sprint length: 2 weeks
- Team: 3-5 engineers (Backend, CV/OCR, Frontend, QA/DevOps)
- Primary objective: ship a production-like POC for multi-format document comparison

---

## Sprint 0 — Project Setup & Delivery Foundation
**Goal:** Establish development baseline and delivery workflow.

### Checklist
- [ ] Finalize scope for POC (must-have vs later features)
- [ ] Define non-functional targets (latency, throughput, FP-rate)
- [ ] Create architecture decision records (ADRs) for key choices
- [ ] Setup repository standards (branching, commit conventions, PR template)
- [ ] Add Python tooling (ruff/black/mypy + pre-commit)
- [ ] Setup baseline CI (lint + unit tests)
- [ ] Create local runtime stack (FastAPI + Redis + Postgres + MinIO via Docker Compose)
- [ ] Add centralized config management (`.env`, settings module)
- [ ] Implement structured logging and request/job correlation IDs
- [ ] Create initial benchmark dataset folders and naming rules

### Deliverables
- Working dev environment for all team members
- CI pipeline running on each PR
- Initial benchmark fixture structure

### Exit Criteria
- [ ] Any new contributor can run project locally in <= 30 min
- [ ] CI pass is required for merge

---

## Sprint 1 — Core Job Workflow + PDF/Image Baseline
**Goal:** End-to-end compare job for PDF/images with persisted job metadata.

### Backend/API
- [ ] Replace in-memory job store with DB-backed job table
- [ ] Add job state transitions (`queued`, `running`, `completed`, `failed`)
- [ ] Add upload validation (size, MIME, extension, duplicate upload detection)
- [ ] Save uploaded files to storage abstraction (local/MinIO)
- [ ] Add result schema versioning (`result_schema_version`)
- [ ] Add basic retry + error handling contract

### Comparison Engine (Baseline)
- [ ] Implement file-type routing pipeline
- [ ] Add PDF page rendering module (PyMuPDF)
- [ ] Add image normalization (resize + grayscale path)
- [ ] Add baseline text extraction (native PDF text if available)
- [ ] Add baseline text diff (`difflib`/token diff)
- [ ] Add baseline visual diff (SSIM + contour boxes)
- [ ] Produce normalized JSON result + HTML report stub

### QA
- [ ] Add unit tests for job lifecycle
- [ ] Add API integration tests for all endpoints + error paths
- [ ] Add golden tests for simple PDF/image compare fixtures

### Exit Criteria
- [ ] Upload 2 PDFs or images, get deterministic result JSON + HTML report
- [ ] Job failures are captured with reason and surfaced via API

---

## Sprint 2 — Scanned Document Robustness (Rotation/Deskew/OCR)
**Goal:** Reduce false positives for scanned docs and camera captures.

### OCR & Preprocessing
- [ ] Integrate PaddleOCR service wrapper
- [ ] Add orientation detection and rotation correction
- [ ] Add deskew pipeline (Hough/line-based)
- [ ] Add denoise + thresholding + contrast enhancement toggles
- [ ] Add OCR confidence filtering and token cleanup
- [ ] Add OCR block grouping (line -> paragraph)

### Alignment
- [ ] Implement coarse page alignment (scale/orientation normalization)
- [ ] Implement feature-based alignment (ORB + homography)
- [ ] Add fine alignment refinement (ECC optional)
- [ ] Persist alignment matrices for debug/replay

### QA/Benchmarking
- [ ] Build scanned-doc benchmark set (rotated, skewed, noisy)
- [ ] Track precision/recall + false positive rate
- [ ] Add regression tests for rotated/scanned cases

### Exit Criteria
- [ ] Rotation/skewed scan cases process successfully
- [ ] False positive rate reduced against Sprint 1 baseline

---

## Sprint 3 — DOCX Structural Comparison
**Goal:** Detect Word-level textual + structural changes.

### Parser & Model
- [ ] Implement DOCX parser (paragraphs, runs, tables, headers/footers)
- [ ] Extract style metadata (font, size, emphasis, alignment)
- [ ] Extract embedded images metadata
- [ ] Map DOCX content into Unified Document Model (UDM)

### Diffing
- [ ] Add paragraph/run-level textual diff
- [ ] Add formatting diff classifier
- [ ] Add table structural diff (row/col add/remove, cell value changes)
- [ ] Add reorder/move detection heuristics for sections/paragraphs

### Reporting
- [ ] Add DOCX-specific change categories in JSON and HTML report
- [ ] Add confidence/severity scoring for each change

### Exit Criteria
- [ ] DOCX changes are grouped by category and rendered in report

---

## Sprint 4 — XLSX Comparison Engine
**Goal:** Spreadsheet-aware comparison with cell/formula intelligence.

### Parser & Diff
- [ ] Implement workbook/sheet parser (openpyxl)
- [ ] Detect sheet add/remove/rename
- [ ] Add cell-level value diff
- [ ] Add formula diff with normalized formula parsing
- [ ] Add row/column insertion/deletion detection
- [ ] Add style/format diff (optional thresholded)
- [ ] Handle hidden rows/columns/sheets metadata changes

### Reporting
- [ ] Add sheet-level summary and drill-down views
- [ ] Export machine-readable changed-cell list

### Exit Criteria
- [ ] XLSX comparison supports multi-sheet workbooks with formula awareness

---

## Sprint 5 — PPT/PPTX Comparison
**Goal:** Slide-aware object-level comparison.

### Parsing
- [ ] Implement PPTX object extraction (textbox, shape, table, image)
- [ ] Add slide rendering pipeline for visual diff overlays
- [ ] Add slide mapping and reorder detection

### Diffing
- [ ] Add textbox text diff + style diff
- [ ] Add shape and table object diff
- [ ] Add embedded image diff hooks (hash/SSIM)

### Exit Criteria
- [ ] PPTX reports slide-level and object-level modifications

---

## Sprint 6 — Unified Model, API Hardening & Frontend Viewer
**Goal:** Stabilize one cross-format contract + operator-friendly UI.

### Unified Model/API
- [ ] Finalize UDM schema and validation contracts
- [ ] Add backward-compatible API response versioning
- [ ] Add pagination/filtering for large result sets
- [ ] Add signed report download URLs (if using object storage)

### Frontend
- [ ] Build upload + compare job submission UI
- [ ] Build job status polling and history list
- [ ] Build side-by-side viewer with overlay boxes
- [ ] Add change list sidebar with filters (type/severity/page)
- [ ] Add synchronized navigation (page/slide/sheet)

### Exit Criteria
- [ ] Stakeholder demo flow fully functional end-to-end

---

## Sprint 7 — Semantic Layer + Risk Summaries
**Goal:** Reduce noise and provide business-meaningful change insights.

### Semantic Intelligence
- [ ] Integrate embedding model service (BGE/Jina/GTE)
- [ ] Add semantic similarity scoring for changed blocks
- [ ] Label changes: wording-only vs meaning-changed
- [ ] Add move/reorder semantic matching across sections/pages

### AI Summaries
- [ ] Create prompt templates for change summary and risk explanation
- [ ] Add high-risk rule templates (finance/legal/compliance)
- [ ] Add optional local LLM summarization pipeline

### Exit Criteria
- [ ] Reports include semantic + risk summary section with confidence

---

## Sprint 8 — Production Readiness & Performance
**Goal:** Make system reliable, observable, and scalable for pilot usage.

### Reliability & Ops
- [ ] Move background work to Celery workers
- [ ] Add retry policy + dead-letter queue
- [ ] Add idempotency keys for compare jobs
- [ ] Add audit logs for job lifecycle and report access
- [ ] Add monitoring dashboards (latency, failures, queue depth)
- [ ] Add alerting for worker failures and SLA breaches

### Security
- [ ] Add authN/authZ (JWT/API keys)
- [ ] Add file sanitization and malware scan hook
- [ ] Add PII-safe logging policy

### Performance
- [ ] Build load test scenarios (small/medium/large docs)
- [ ] Profile bottlenecks (OCR, alignment, rendering)
- [ ] Add caching and batching where valuable

### Exit Criteria
- [ ] Pilot-ready deployment with SLA and observability baseline

---

## Cross-Sprint Definition of Done (DoD)
For every user story/task:
- [ ] Code implemented and reviewed
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Documentation updated (API and architecture where impacted)
- [ ] Logging and error handling included
- [ ] Benchmark impact recorded (if diff engine path changed)
- [ ] Security/privacy checklist passed

---

## Master Tracking Checklist (Program Level)
- [ ] Sprint 0 complete
- [ ] Sprint 1 complete
- [ ] Sprint 2 complete
- [ ] Sprint 3 complete
- [ ] Sprint 4 complete
- [ ] Sprint 5 complete
- [ ] Sprint 6 complete
- [ ] Sprint 7 complete
- [ ] Sprint 8 complete
- [ ] POC acceptance criteria met
- [ ] Stakeholder demo sign-off
- [ ] Pilot rollout readiness review passed
