from fastapi import FastAPI

from app.api.routes import router as api_router

app = FastAPI(title="COMPARION API", version="0.1.0")
app.include_router(api_router, prefix="/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
