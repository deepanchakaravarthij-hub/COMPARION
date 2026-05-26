# POC Scope

## Must Have

- FastAPI upload and job lifecycle endpoints.
- Persisted comparison jobs and result metadata.
- PDF and image comparison with baseline text and visual diff.
- Scanned document preprocessing with OCR, rotation correction, deskew, and alignment.
- Stable JSON result schema and HTML report.
- Benchmark fixtures and repeatable regression tests.
- Structured logs with request and job correlation IDs.

## Should Have

- DOCX structural diff.
- XLSX cell and formula diff.
- PPTX slide and object diff.
- Frontend viewer with side-by-side overlays.
- Semantic change labels and risk summaries.

## Later

- Enterprise RBAC and approval workflows.
- Multi-tenant compliance certification.
- Real-time collaboration.
- Full document lifecycle management.

## Out of Scope for Initial POC

- Cross-format comparison.
- Auto-remediation of document changes.
- Production-grade malware scanning beyond a pluggable hook.
- Guaranteed legal or compliance classification.
