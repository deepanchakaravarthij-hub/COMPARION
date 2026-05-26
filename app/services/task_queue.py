from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import BackgroundTasks

from app.core.config import get_settings


def enqueue_compare_job(
    background_tasks: BackgroundTasks,
    job_callable: Callable[..., None],
    *args: Any,
) -> dict[str, Any]:
    settings = get_settings()
    mode = settings.queue_mode.lower()
    if mode == "celery":
        _enqueue_celery(job_callable, *args)
        return {"mode": "celery", "queued": True}

    background_tasks.add_task(job_callable, *args)
    return {"mode": "inline", "queued": True}


def _enqueue_celery(job_callable: Callable[..., None], *args: Any) -> None:
    try:
        from celery import Celery  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - exercised by runtime configuration.
        raise RuntimeError(
            "COMPARION_QUEUE_MODE=celery requires Celery to be installed."
        ) from exc

    settings = get_settings()
    celery_app = Celery(
        "comparion",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
    )

    @celery_app.task(name="comparion.run_compare_job")  # type: ignore[untyped-decorator]
    def _task(payload: list[Any]) -> None:
        job_callable(*payload)

    _task.delay(list(args))
