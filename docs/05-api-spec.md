# API Spec (POC)

- `POST /v1/compare` upload two files and options.
- `GET /v1/jobs/{job_id}` job status/progress.
- `GET /v1/jobs/{job_id}/result` normalized JSON result.
- `GET /v1/jobs/{job_id}/report.html` downloadable report.

Request includes:
- file_a, file_b
- compare_mode
- thresholds
- enable_semantic

## Sprint 2 Response Contract

Result JSON includes:
- `result_schema_version`
- `summary`
- `file_type`
- `changes`
- optional `diagnostics`

Each change includes:
- `id`
- `type`
- `category`
- `severity`
- `confidence`
- `message`
- `source_ref`
- optional `bbox`

The report endpoint returns HTML once the job is completed and returns `409` while the job is incomplete.

Sprint 2 uses `result_schema_version` `2.0` and may include diagnostics for preprocessing, alignment, debug artifacts, and benchmark metrics.
