# COMPARION

Starter FastAPI backend for multi-format document comparison POC.

## Run
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Current endpoints
- `GET /health`
- `POST /v1/compare`
- `GET /v1/jobs/{job_id}`
- `GET /v1/jobs/{job_id}/result`

This is a Phase-0/Phase-1 scaffold with in-memory job storage and baseline binary comparator.
