from fastapi import FastAPI

from app.api.routes import router as api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, request_context_middleware

settings = get_settings()
configure_logging(settings)

app = FastAPI(title=settings.app_name, version="0.1.0")
app.middleware("http")(request_context_middleware)
app.include_router(api_router, prefix="/v1")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
