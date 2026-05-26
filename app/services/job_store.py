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


init_db()
