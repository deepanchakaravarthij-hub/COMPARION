# Pilot Sizing and Load Testing

## Scope

This document defines pilot load-test scenarios, expected operating ranges, and baseline alert thresholds for Sprint 8 production hardening.

## Load-Test Scenarios

Use `python scripts/load_test.py` to validate the end-to-end compare workflow.

Recommended scenarios:

1. Small docs
   - `--requests 30 --concurrency 6`
   - Input: short PDFs / compact DOCX / XLSX / PPTX
2. Medium docs
   - `--requests 20 --concurrency 4`
   - Input: multi-page/multi-sheet/multi-slide files
3. Large docs
   - `--requests 10 --concurrency 2`
   - Input near `COMPARION_MAX_UPLOAD_MB` with rich formatting and images

## Initial Sizing Assumptions

- API workers: 2-4 FastAPI workers
- Queue mode: `inline` for local, `celery` for pilot/staging
- Broker: Redis for Celery transport
- Database: SQLite for POC; migrate to Postgres for concurrent pilot traffic
- Storage: local disk for POC; object storage with signed URLs for pilot

## Baseline Alerts

Configured by settings:

- `COMPARION_METRICS_ALERT_FAILURE_RATE_THRESHOLD` (default `0.15`)
- `COMPARION_METRICS_ALERT_QUEUE_DEPTH_THRESHOLD` (default `20`)

Alert behavior:

- Failure-rate alert when `failed / total` exceeds threshold
- Queue-depth alert when `queued + running` exceeds threshold

## Retention and Cleanup

- Retention period: `COMPARION_RETENTION_DAYS` (default `7`)
- Cleanup endpoint: `POST /v1/ops/retention/cleanup`
- Cleanup removes expired job metadata and old storage artifacts

## Known Limits (Current POC)

- In-process compare execution can saturate API workers under heavy load
- Celery execution mode requires external broker and worker lifecycle management
- SQLite is not suitable for high write concurrency beyond pilot-scale traffic
- Malware scan hook relies on external command; pipeline behavior depends on command correctness
