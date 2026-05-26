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
