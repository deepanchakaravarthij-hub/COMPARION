from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.core.config import get_settings

JobRecord = dict[str, Any]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _database_path() -> Path:
    database_url = get_settings().database_url
    if not database_url.startswith("sqlite:///"):
        raise RuntimeError("Sprint 1 persistence supports sqlite:/// database URLs")
    path = Path(database_url.removeprefix("sqlite:///"))
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect() -> sqlite3.Connection:
    connection = sqlite3.connect(_database_path(), check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with _connect() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                file_a TEXT NOT NULL,
                file_b TEXT NOT NULL,
                file_a_type TEXT NOT NULL,
                file_b_type TEXT NOT NULL,
                file_a_path TEXT,
                file_b_path TEXT,
                file_a_sha256 TEXT,
                file_b_sha256 TEXT,
                result_json TEXT,
                result_path TEXT,
                report_path TEXT,
                error_code TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT
            )
            """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS idempotency_keys (
                idempotency_key TEXT PRIMARY KEY,
                request_hash TEXT NOT NULL,
                job_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                job_id TEXT,
                request_id TEXT,
                event_type TEXT NOT NULL,
                details_json TEXT,
                created_at TEXT NOT NULL
            )
            """)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS dead_letter_jobs (
                dead_letter_id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                reason TEXT NOT NULL,
                payload_json TEXT,
                created_at TEXT NOT NULL
            )
            """)


def create_job(
    file_a: str,
    file_b: str,
    file_a_type: str,
    file_b_type: str,
    file_a_sha256: str,
    file_b_sha256: str,
) -> str:
    init_db()
    job_id = str(uuid4())
    now = _utc_now()
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO jobs (
                job_id, status, file_a, file_b, file_a_type, file_b_type,
                file_a_sha256, file_b_sha256, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                "queued",
                file_a,
                file_b,
                file_a_type,
                file_b_type,
                file_a_sha256,
                file_b_sha256,
                now,
                now,
            ),
        )
    return job_id


def get_job(job_id: str) -> JobRecord | None:
    init_db()
    with _connect() as connection:
        row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    if row is None:
        return None
    record = dict(row)
    if record.get("result_json"):
        record["result"] = json.loads(record["result_json"])
    else:
        record["result"] = None
    return record


def get_or_create_idempotent_job(
    idempotency_key: str,
    request_hash: str,
    create_job_fn: Any,
) -> tuple[str, bool]:
    init_db()
    now = _utc_now()
    with _connect() as connection:
        existing = connection.execute(
            """
            SELECT job_id, request_hash
            FROM idempotency_keys
            WHERE idempotency_key = ?
            """,
            (idempotency_key,),
        ).fetchone()
        if existing is not None:
            if existing["request_hash"] != request_hash:
                raise ValueError("Idempotency key was already used for a different request payload")
            return str(existing["job_id"]), True

        job_id = str(create_job_fn())
        connection.execute(
            """
            INSERT INTO idempotency_keys (idempotency_key, request_hash, job_id, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (idempotency_key, request_hash, job_id, now),
        )
        return job_id, False


def list_jobs(
    limit: int = 20,
    offset: int = 0,
    status: str | None = None,
) -> tuple[list[JobRecord], int]:
    init_db()
    where = ""
    params: list[Any] = []
    if status:
        where = "WHERE status = ?"
        params.append(status)

    with _connect() as connection:
        total_row = connection.execute(
            f"SELECT COUNT(*) as total FROM jobs {where}",
            tuple(params),
        ).fetchone()
        rows = connection.execute(
            f"""
            SELECT job_id, status, file_a, file_b, file_a_type, created_at, updated_at
            FROM jobs
            {where}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params + [limit, offset]),
        ).fetchall()

    total = int(total_row["total"]) if total_row else 0
    records = [dict(row) for row in rows]
    for record in records:
        record["file_type"] = record.pop("file_a_type")
    return records, total


def summarize_job_statuses() -> dict[str, int]:
    init_db()
    statuses = {"queued": 0, "running": 0, "completed": 0, "failed": 0, "cancelled": 0}
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT status, COUNT(*) as total
            FROM jobs
            GROUP BY status
            """
        ).fetchall()
    for row in rows:
        statuses[str(row["status"])] = int(row["total"])
    return statuses


def set_job_files(job_id: str, file_a_path: str, file_b_path: str) -> None:
    now = _utc_now()
    with _connect() as connection:
        connection.execute(
            """
            UPDATE jobs
            SET file_a_path = ?, file_b_path = ?, updated_at = ?
            WHERE job_id = ?
            """,
            (file_a_path, file_b_path, now, job_id),
        )


def set_job_status(job_id: str, status: str) -> None:
    now = _utc_now()
    started_at = now if status == "running" else None
    with _connect() as connection:
        if started_at:
            connection.execute(
                """
                UPDATE jobs
                SET status = ?, started_at = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (status, started_at, now, job_id),
            )
        else:
            connection.execute(
                "UPDATE jobs SET status = ?, updated_at = ? WHERE job_id = ?",
                (status, now, job_id),
            )


def set_job_result(
    job_id: str,
    result: dict[str, Any],
    result_path: str,
    report_path: str,
) -> None:
    now = _utc_now()
    with _connect() as connection:
        connection.execute(
            """
            UPDATE jobs
            SET status = ?, result_json = ?, result_path = ?, report_path = ?,
                completed_at = ?, updated_at = ?
            WHERE job_id = ?
            """,
            (
                "completed",
                json.dumps(result, sort_keys=True),
                result_path,
                report_path,
                now,
                now,
                job_id,
            ),
        )


def set_job_failed(job_id: str, error_code: str, error_message: str) -> None:
    now = _utc_now()
    with _connect() as connection:
        connection.execute(
            """
            UPDATE jobs
            SET status = ?, error_code = ?, error_message = ?, completed_at = ?, updated_at = ?
            WHERE job_id = ?
            """,
            ("failed", error_code, error_message, now, now, job_id),
        )


def add_audit_event(
    event_type: str,
    job_id: str | None = None,
    request_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    now = _utc_now()
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO audit_events (
                event_id, job_id, request_id, event_type, details_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                job_id,
                request_id,
                event_type,
                json.dumps(details or {}, sort_keys=True),
                now,
            ),
        )


def add_dead_letter_job(
    job_id: str,
    reason: str,
    payload: dict[str, Any] | None = None,
) -> None:
    now = _utc_now()
    with _connect() as connection:
        connection.execute(
            """
            INSERT INTO dead_letter_jobs (dead_letter_id, job_id, reason, payload_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                job_id,
                reason,
                json.dumps(payload or {}, sort_keys=True),
                now,
            ),
        )


def cleanup_expired_jobs(retention_days: int) -> dict[str, int]:
    init_db()
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT job_id, file_a_path, file_b_path, result_path, report_path
            FROM jobs
            WHERE completed_at IS NOT NULL
              AND julianday('now') - julianday(completed_at) > ?
            """,
            (retention_days,),
        ).fetchall()
        job_ids = [str(row["job_id"]) for row in rows]
        deleted_count = 0
        if job_ids:
            placeholders = ",".join("?" for _ in job_ids)
            connection.execute(
                f"DELETE FROM jobs WHERE job_id IN ({placeholders})",
                tuple(job_ids),
            )
            deleted_count = len(job_ids)
    return {"deleted_jobs": deleted_count, "expired_artifacts": len(rows)}


init_db()
