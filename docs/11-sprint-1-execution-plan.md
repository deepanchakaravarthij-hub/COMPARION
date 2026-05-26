# Sprint 1 Execution Plan

## Sprint Goal

Upgrade the Phase 0 scaffold into an end-to-end PDF/image comparison workflow with persisted job metadata, validated uploads, stored artifacts, deterministic result JSON, and an HTML report stub.

## Sprint Outcome

By the end of Sprint 1, a user can upload two PDFs or images, poll job status, fetch normalized result JSON, and download a basic HTML report. Job state and failure details are persisted instead of held only in memory.

## Scope

### In Scope

- DB-backed job lifecycle.
- Local storage abstraction with MinIO-ready interface.
- Upload validation for filename, size, MIME type, extension, and duplicate uploads.
- PDF and image routing.
- PDF page rendering with PyMuPDF.
- Basic image normalization.
- Native PDF text extraction where available.
- Baseline token/text diff.
- Baseline visual diff using SSIM and bounding boxes.
- Result schema versioning.
- HTML report stub.
- API and golden-path tests.

### Out of Scope

- OCR for scanned documents.
- Rotation correction, deskew, homography alignment, and scan robustness.
- DOCX, XLSX, and PPTX parsing.
- Frontend viewer.
- Celery production worker architecture.
- Authentication and authorization.

## Workstreams

## 1. Data Model and Persistence

### Tasks

- [ ] Add SQLAlchemy or SQLModel dependency and database session setup.
- [ ] Define `jobs` table with `job_id`, status, filenames, file types, timestamps, error fields, and result/report references.
- [ ] Define job status enum: `queued`, `running`, `completed`, `failed`, `cancelled`.
- [ ] Add migration strategy placeholder or initial SQL bootstrap script.
- [ ] Replace `app/services/job_store.py` in-memory implementation with repository/service methods backed by the database.
- [ ] Persist `created_at`, `updated_at`, `started_at`, and `completed_at`.
- [ ] Persist failure reason and internal error code.

### Acceptance Checks

- [ ] Jobs survive app process restart when using Postgres.
- [ ] Missing job returns `404`.
- [ ] Incomplete job result returns `409`.
- [ ] Failed job response includes a clear reason.

## 2. Storage Abstraction

### Tasks

- [ ] Add storage service interface for `save`, `open/read`, and `url/path` operations.
- [ ] Implement local filesystem storage first.
- [ ] Keep MinIO configuration ready through existing settings.
- [ ] Store original uploads under deterministic job-scoped paths.
- [ ] Store result JSON and report HTML under deterministic job-scoped paths.
- [ ] Add safeguards against unsafe filenames and path traversal.

### Acceptance Checks

- [ ] Uploaded files are saved outside source code directories.
- [ ] Result JSON and report HTML can be retrieved by job ID.
- [ ] Storage paths do not expose raw user filenames directly.

## 3. API Contract

### Tasks

- [ ] Extend `POST /v1/compare` to validate upload size, MIME type, and extension.
- [ ] Return `job_id`, status, and request correlation metadata.
- [ ] Extend `GET /v1/jobs/{job_id}` with timestamps, file names, file types, and optional error summary.
- [ ] Extend `GET /v1/jobs/{job_id}/result` with schema version and normalized change list.
- [ ] Add `GET /v1/jobs/{job_id}/report.html`.
- [ ] Add consistent error response model for validation, not found, conflict, and processing failure cases.

### Acceptance Checks

- [ ] API rejects unsupported extensions.
- [ ] API rejects missing filenames.
- [ ] API rejects files over configured size.
- [ ] Report endpoint returns HTML for completed jobs and `409` before completion.

## 4. Comparison Pipeline

### Tasks

- [ ] Add file-type router for PDF and image inputs.
- [ ] Return a controlled failure for unsupported but recognized future types.
- [ ] Add PDF renderer module using PyMuPDF.
- [ ] Add native PDF text extraction module.
- [ ] Add image loader and normalization module.
- [ ] Add baseline text diff using token-level comparison.
- [ ] Add baseline visual diff with SSIM and contour bounding boxes.
- [ ] Emit normalized coordinates between `0` and `1`.
- [ ] Add deterministic result ordering.

### Acceptance Checks

- [ ] Identical PDF/image pair returns no changes.
- [ ] Modified PDF/image pair returns at least one change.
- [ ] Different supported file types return a validation or controlled mismatch response.
- [ ] Repeated runs on the same fixtures produce stable JSON.

## 5. Result Schema and Report

### Tasks

- [ ] Add `result_schema_version`.
- [ ] Define change fields: `id`, `type`, `category`, `severity`, `confidence`, `message`, `source_ref`, and optional `bbox`.
- [ ] Define page-level source references for PDF/image results.
- [ ] Generate report HTML with summary, file metadata, and change list.
- [ ] Include report generation errors in job failure handling.

### Acceptance Checks

- [ ] Result JSON validates through Pydantic schemas.
- [ ] HTML report includes job ID, summary, file names, and changes.
- [ ] Empty-change report renders cleanly.

## 6. Testing and Benchmarks

### Tasks

- [ ] Add unit tests for job repository state transitions.
- [ ] Add unit tests for upload validation.
- [ ] Add unit tests for file-type routing.
- [ ] Add API integration tests for compare, status, result, report, and error paths.
- [ ] Add small PDF and image benchmark fixtures.
- [ ] Add golden expected JSON for simple fixtures.
- [ ] Add CI test command coverage for new tests.

### Acceptance Checks

- [ ] `ruff check .` passes.
- [ ] `black --check .` passes.
- [ ] `mypy app` passes.
- [ ] `pytest` passes.
- [ ] Golden tests fail on nondeterministic result ordering.

## Suggested Implementation Order

1. Define Sprint 1 result schema and job status models.
2. Add database session and job repository.
3. Replace in-memory job store while keeping current API behavior green.
4. Add storage abstraction and save uploads.
5. Add upload validation and error response model.
6. Add PDF/image routing and baseline comparison modules.
7. Add result JSON persistence.
8. Add report generation and report endpoint.
9. Add benchmark fixtures and golden tests.
10. Update API docs and README.

## Risks and Mitigations

- **PyMuPDF and OpenCV dependency setup may slow local installs.** Keep imports isolated inside engine modules and document platform notes.
- **BackgroundTasks are not durable.** Accept for Sprint 1 POC, but persist status and failure details so the service is ready for Celery in Sprint 8.
- **Visual diff may produce noisy boxes.** Keep thresholds configurable and record benchmark output rather than tuning blindly.
- **Result schema may shift later.** Use `result_schema_version` from the start and keep Sprint 1 fields minimal.

## Demo Script

1. Start local services with Docker Compose.
2. Submit two simple PDFs to `POST /v1/compare`.
3. Poll `GET /v1/jobs/{job_id}` until `completed`.
4. Fetch `GET /v1/jobs/{job_id}/result`.
5. Open `GET /v1/jobs/{job_id}/report.html`.
6. Repeat with two simple images.
7. Show a rejected unsupported file and a rejected oversized upload.

## Sprint 1 Definition of Done

- [x] All in-scope API paths implemented.
- [x] Job data is persisted.
- [x] Uploaded files and generated artifacts are stored through the storage abstraction.
- [x] PDF/image baseline comparisons produce deterministic JSON.
- [x] HTML report endpoint works.
- [x] Tests and golden fixtures are committed.
- [x] Documentation is updated.
- [x] Sprint 1 checklist in `sprint_plan.md` is updated.
