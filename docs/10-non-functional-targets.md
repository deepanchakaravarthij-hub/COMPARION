# Non-Functional Targets

These targets define the initial POC operating envelope. They should be revised as benchmark data becomes available.

## Performance

- Small documents, 1-5 pages: complete within 30 seconds.
- Medium documents, 6-50 pages: complete within 3 minutes.
- Large documents, 51-200 pages: complete within 10 minutes for pilot usage.
- API status endpoints should respond within 300 ms under normal load.

## Quality

- False-positive rate at or below 10% on the curated benchmark set.
- Deterministic JSON result ordering for repeated runs on the same fixture pair.
- OCR confidence and comparison confidence must be exposed for scan-driven changes.

## Reliability

- Failed jobs must preserve failure reason and timestamps.
- Background work should be retryable for transient failures.
- Job creation must become idempotent before pilot rollout.

## Security and Privacy

- Logs must not include document text or uploaded file contents.
- Uploaded files and generated reports must have a documented retention policy.
- Authentication and authorization are required before pilot rollout.

## Operability

- Every request includes an `X-Request-ID` response header.
- Job logs include a job correlation ID once persistent jobs are implemented.
- Metrics should cover latency, failures, queue depth, and worker health before pilot rollout.
