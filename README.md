# COMPARION

Starter FastAPI backend for a multi-format document comparison POC.

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`.

## Docker Compose

```bash
copy .env.example .env
docker compose up --build
```

This starts:

- FastAPI API on port `8000`
- Postgres on port `5432`
- Redis on port `6379`
- MinIO on ports `9000` and `9001`

## Current Endpoints

- `GET /health`
- `POST /v1/compare`
- `GET /v1/jobs/{job_id}`
- `GET /v1/jobs/{job_id}/result`
- `GET /v1/jobs/{job_id}/report.html`

This is a Phase 2 scaffold with SQLite job storage, local artifact storage, baseline PDF/image comparison, and scan preprocessing/alignment diagnostics.
Uploads, result JSON, and report HTML are written under `storage/`.

## Development Checks

```bash
ruff check .
black --check .
mypy app
pytest
```

Optional pre-commit setup:

```bash
pre-commit install
pre-commit run --all-files
```

## Documentation

- `plan.md` - master implementation plan and phase roadmap.
- `sprint_plan.md` - detailed execution checklist by sprint.
- `docs/` - architecture, UDM, API, testing, deployment, ADRs, and POC scope.
- `benchmarks/` - benchmark fixture layout and expected-output rules.
