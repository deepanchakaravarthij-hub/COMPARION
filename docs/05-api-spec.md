# API Spec (POC)

## Endpoints

- `POST /v1/compare` submit two files for comparison.
- `GET /v1/jobs` list recent jobs with pagination.
- `GET /v1/jobs/{job_id}` fetch job status and metadata.
- `GET /v1/jobs/{job_id}/result` fetch result JSON with schema versioning, filtering, and pagination.
- `GET /v1/jobs/{job_id}/report-link` fetch report URL (signed when object storage mode is enabled).
- `GET /v1/jobs/{job_id}/report.html` fetch HTML report.
- `GET /v1/jobs/{job_id}/artifact-link/{label}` fetch artifact URL for `a` or `b`.
- `GET /v1/jobs/{job_id}/artifact/{label}` fetch original uploaded artifact for native viewers.
- `GET /viewer` open built-in operator viewer UI.

## Compare Request

`POST /v1/compare` uses multipart upload:

- `file_a`
- `file_b`

Both files must have the same supported type:
- `pdf`
- `image` (`png`, `jpg`, `jpeg`, `tif`, `tiff`, `bmp`, `webp`)
- `docx`
- `xlsx`
- `pptx`

## Result Contract (Schema 2.1)

Result payload fields:
- `result_schema_version`
- `summary`
- `file_type`
- `changes[]`
- optional `diagnostics`
- optional `udm` (Unified Document Model view)
- optional `viewer_hints` (renderer, anchors, filter lists, and normalized coordinate policy)
- optional `pagination` metadata

Each `changes[]` entry includes:
- `id`
- `type`
- `category`
- `severity`
- `confidence`
- `message`
- `source_ref`
- optional `bbox`

## Backward-Compatible Versioning

`GET /v1/jobs/{job_id}/result` supports:

- `result_schema_version=2.1` (default)
- `result_schema_version=2.0` (legacy-compatible category/source mapping)

## Result Filtering and Pagination

`GET /v1/jobs/{job_id}/result` query parameters:

- `offset` (default `0`)
- `limit` (optional)
- `category`
- `severity`
- `change_type`
- `search`

Response includes `pagination`:
- `offset`
- `limit`
- `total_filtered`
- `total_changes`
- `has_more`

## Signed Report URLs

When `COMPARION_OBJECT_STORAGE_ENABLED=true`:

- `GET /v1/jobs/{job_id}/report-link` returns a signed URL with token and expiration.
- `GET /v1/jobs/{job_id}/report.html` requires valid `token` and `expires` query parameters.

When disabled, report-link returns direct `/v1/jobs/{job_id}/report.html`.

## Native Viewer Artifact Access

Next.js native viewers should request original uploads using:

- `GET /v1/jobs/{job_id}/artifact-link/a`
- `GET /v1/jobs/{job_id}/artifact-link/b`

When object storage mode is enabled, these links include signed `token` and `expires` query
parameters. The artifact endpoint records audit events and returns the original upload with an
appropriate media type.

## Format Examples

### PDF / Image
- Category examples: `text`, `visual`, `metadata`
- Source examples: `{ "document": "both", "page": 1 }`

### DOCX
- Category examples: `text`, `formatting`, `table`, `image`, `structure`
- Source examples: `{ "document": "both", "part": "body", "paragraph": 3, "run": 2 }`

### XLSX
- Category examples: `sheet`, `formula`, `text`, `formatting`, `structure`, `metadata`
- Source examples: `{ "document": "both", "sheet": "Summary", "cell": "B2" }`

### PPTX
- Category examples: `text`, `formatting`, `table`, `image`, `structure`, `visual`
- Source examples: `{ "document": "both", "slide": 2 }`
