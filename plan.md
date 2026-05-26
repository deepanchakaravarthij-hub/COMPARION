# COMPARION POC Plan

## Goal
Build a robust POC to compare two versions of documents across **PDF, DOCX, XLSX, PPTX, Images, and scanned documents**, detecting textual, structural, and visual differences with strong edge-case handling (rotation, skew, OCR noise, embedded images).

## POC Success Criteria
- Compare two documents of same type (Phase 1-3), produce structured diff JSON and HTML report.
- Highlight added/removed/modified content with page/slide/cell coordinates.
- Handle scanned/rotated inputs with normalization + alignment to reduce false positives.
- Return explainable confidence scores for each detected change.

## Scope Boundaries
### In scope (POC)
- Multi-format ingestion (PDF, image first; then DOCX/XLSX/PPTX).
- OCR + layout extraction for scanned assets.
- Visual diff overlays and text diff side-by-side.
- Unified internal data model.
- Batch async jobs and downloadable reports.

### Out of scope (initial POC)
- Full enterprise RBAC/workflow approvals.
- Real-time collaboration.
- Cross-tenant compliance certifications.
- LLM-heavy auto-remediation.

## Architecture (High-level)
1. **Upload/API Layer** (FastAPI)
2. **Normalization Layer** (render, rotate, deskew, denoise, align)
3. **Extraction Layer** (text/layout/tables/images)
4. **Unified Document Model (UDM)**
5. **Diff Engines** (text, structure, visual, semantic)
6. **Report Layer** (JSON + HTML, optional PDF export)
7. **Async Orchestration** (Celery + Redis)

## Phased Execution Plan

### Phase 0 — Foundation (3-5 days)
- Repo scaffolding, service contracts, docker-compose.
- FastAPI upload endpoint + background job scaffolding.
- Storage setup (local + MinIO abstraction).
- Observability baseline (structured logs + metrics stubs).

Deliverables:
- Running API + worker skeleton
- Sample job lifecycle endpoints

### Phase 1 — Core PDF/Image/Scanned Compare (2 weeks)
- PDF/page rendering (PyMuPDF)
- Image normalization (denoise, deskew, rotate detect)
- OCR extraction + confidence filtering (PaddleOCR)
- Page alignment (ORB + homography + optional ECC refine)
- Text diff and visual diff (SSIM + contour bbox)
- HTML report with overlays

Deliverables:
- Robust compare for PDFs/images/scanned docs
- Rotated page handling and reduced false positives

### Phase 2 — DOCX Structural Diff (1 week)
- Parse paragraphs/runs/tables/headers/footers/images.
- Normalize XML-backed structure into UDM blocks.
- Detect formatting + ordering + table changes.

Deliverables:
- Paragraph/table/format change detection with coordinates/index mapping

### Phase 3 — XLSX Diff (1 week)
- Cell-level and formula-level comparison.
- Sheet add/remove, row/column insert/delete.
- Formatting and hidden-sheet metadata diffs.

Deliverables:
- Structured spreadsheet diff report

### Phase 4 — PPTX Diff (1 week)
- Slide-level parsing + render to image.
- Object-level diff (text box, shapes, tables, images).
- Slide reorder detection and visual overlays.

Deliverables:
- Slide-aware diff output for PPT/PPTX

### Phase 5 — Unified Intelligence Layer (1 week)
- Stabilize UDM across all types.
- Cross-format standard result schema.
- Confidence scoring and diff severity taxonomy.

Deliverables:
- One canonical comparison output format

### Phase 6 — Semantic Layer (1 week)
- Embedding-based semantic matching (BGE/Jina/GTE).
- Reorder/paraphrase detection to suppress false positives.
- Optional “meaning changed vs wording changed” labels.

Deliverables:
- Semantic-aware diff annotations

### Phase 7 — AI Explanation + Risk (1 week)
- LLM summaries for critical changes.
- Domain risk classification (financial/legal/compliance templates).

Deliverables:
- Human-readable change summary and risk section

### Phase 8 — Hardening (ongoing)
- Retry strategy, job idempotency, failure recovery.
- Benchmarking, regression suite, scale tests.
- Security hardening and audit trails.

## Key Technical Decisions
- **Normalize first, compare second** (core principle).
- **Use normalized coordinates (0..1) everywhere**, never raw pixels.
- **Block-level alignment over full-page-only alignment** to reduce drift.
- **Confidence gating** at OCR token and change levels.

## Critical Edge Cases and Mitigations
- Rotated pages/images → orientation classifier + Hough fallback.
- Skewed/camera scans → deskew + perspective correction.
- Embedded images/signatures/stamps → segmentation and region-type-specific comparators.
- OCR noise → confidence thresholds, merge heuristics, cleanup rules.
- Layout shifts/margins/resolution changes → multistage alignment and normalized coordinates.
- Table structure drift → table-aware extraction and structural diff.

## Core Tech Stack
- API: FastAPI
- Worker queue: Celery + Redis
- OCR/layout: PaddleOCR (+ PP-Structure optional)
- Vision/alignment: OpenCV
- PDF render/parse: PyMuPDF
- DOCX: python-docx + lxml
- XLSX: openpyxl + pandas
- PPTX: python-pptx (+ LibreOffice render path)
- Visual similarity: scikit-image SSIM
- Semantic: sentence-transformers + FAISS
- Storage: MinIO/local
- DB: PostgreSQL
- Frontend: Next.js + react-pdf + canvas overlays

## Milestone Demo Scenario
- Input: two contract PDFs (one scanned, rotated, with signature/image edits).
- Output: side-by-side viewer, changed clauses, visual heatmap boxes, summary of high-risk modifications.

## Acceptance Criteria (POC)
- <= 10% false-positive rate on curated benchmark set.
- Rotation + skew handling on scanned pages with stable overlays.
- End-to-end job completion and downloadable HTML report.
- Deterministic JSON schema across supported formats.
