# Architecture

## Services
- API service (FastAPI)
- Worker service (Celery)
- Extraction services (parser/ocr/layout)
- Diff services (text/structure/visual/semantic)
- Report service (HTML/JSON)

## Pipeline
Upload -> normalize -> extract -> UDM -> diff -> score -> report.

## Data flow contracts
- Every stage emits typed JSON with trace IDs.
- All coordinates normalized to page space (0..1).
