# COMPARION Next.js UI

Standalone frontend for the FastAPI comparison backend.

## Setup

```bash
npm install
cp .env.example .env.local
npm run dev
```

Set `NEXT_PUBLIC_API_BASE_URL` to the FastAPI origin. If backend auth is enabled, set
`NEXT_PUBLIC_AUTH_MODE` to `api-key` or `bearer` and enter the token in the UI.

## Validation

```bash
npm run typecheck
npm run build
npm run test:e2e
```

The UI supports upload, job history, polling, artifact loading, side-by-side native renderers,
change filters, semantic/risk review, and telemetry events for pilot dashboards.
