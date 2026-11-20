"""
queue_store.py - Broken SQLite job queue store for BENCH-008.
"""
import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Callable, Dict, List, Optional, Union

from models import Job, JobStatus, LeaseError


class QueueStore:
    """
    BROKEN: Uses non-atomic SELECT then UPDATE for job claiming, commits audit log
    separately from job status updates, and never reclaims expired leases.
    """

    def __init__(self, db_path: Union[str, Path]) -> None:
        self.db_path = str(db_path)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL DEFAULT 3,
                    lease_owner TEXT,
                    lease_expires_at REAL,
                    available_at REAL NOT NULL DEFAULT 0.0,
                    last_error TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS job_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    worker_id TEXT,
                    attempt INTEGER NOT NULL,
                    details TEXT,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def _row_to_job(self, row: sqlite3.Row) -> Job:
        return Job(
            job_id=row["job_id"],
            payload=json.loads(row["payload_json"]),
            status=JobStatus(row["status"]),
            attempts=int(row["attempts"]),
            max_attempts=int(row["max_attempts"]),
            available_at=float(row["available_at"]),
            last_error=row["last_error"],
            created_at=float(row["created_at"]),
            updated_at=float(row["updated_at"]),
        )

    def enqueue(
        self,
        job_id: str,
        payload: Dict[str, Any],
        max_attempts: int = 3,
        available_at: float = 0.0,
        now: Optional[float] = None,
    ) -> Job:
        ts = float(time.time() if now is None else now)
        conn = self._connect()
        try:
            conn.execute(
                """
                INSERT INTO jobs (
                    job_id, payload_json, status, attempts, max_attempts,
                    lease_owner, lease_expires_at, available_at, last_error,
                    created_at, updated_at
                ) VALUES (?, ?, ?, 0, ?, NULL, NULL, ?, NULL, ?, ?)
                """,
                (job_id, json.dumps(payload), JobStatus.PENDING.value, max_attempts, available_at, ts, ts),
            )
            conn.execute(
                """
                INSERT INTO job_audit_log (job_id, event_type, worker_id, attempt, details, created_at)
                VALUES (?, 'ENQUEUED', NULL, 0, NULL, ?)
                """,
                (job_id, ts),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            return self._row_to_job(row)
        finally:
            conn.close()

    def claim_next_job(
        self,
        worker_id: str,
        lease_ttl: float = 5.0,
        now: Optional[float] = None,
    ) -> Optional[Job]:
        """BROKEN: Non-atomic SELECT followed by UPDATE allows concurrent claim races."""
        ts = float(time.time() if now is None else now)
        conn = self._connect()
        try:
            row = conn.execute(
                """
                SELECT * FROM jobs
                WHERE status = 'PENDING' AND available_at <= ?
                ORDER BY created_at ASC, rowid ASC
                LIMIT 1
                """,
                (ts,),
            ).fetchone()
            if row is None:
                return None
        finally:
            conn.close()

        # Non-atomic race window between read and write
        time.sleep(0.01)

        conn2 = self._connect()
        try:
            new_attempts = int(row["attempts"]) + 1
            conn2.execute(
                """
                UPDATE jobs
                SET status = 'RUNNING', attempts = ?, lease_owner = ?,
                    lease_expires_at = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (new_attempts, worker_id, ts + lease_ttl, ts, row["job_id"]),
            )
            conn2.execute(
                """
                INSERT INTO job_audit_log (job_id, event_type, worker_id, attempt, details, created_at)
                VALUES (?, 'CLAIMED', ?, ?, NULL, ?)
                """,
                (row["job_id"], worker_id, new_attempts, ts),
            )
            conn2.commit()
            updated = conn2.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (row["job_id"],)
            ).fetchone()
            return self._row_to_job(updated)
        finally:
            conn2.close()

    def complete_job(
        self,
        job_id: str,
        worker_id: str,
        now: Optional[float] = None,
        pre_status_hook: Optional[Callable[[], None]] = None,
    ) -> Job:
        """BROKEN: Commits audit log before status update, causing partial-write leaks."""
        ts = float(time.time() if now is None else now)
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            if row is None:
                raise LeaseError(f"Unknown job: {job_id}")
            # BUG: commits audit row BEFORE verifying lease / running hook / updating job
            conn.execute(
                """
                INSERT INTO job_audit_log (job_id, event_type, worker_id, attempt, details, created_at)
                VALUES (?, 'COMPLETED', ?, ?, NULL, ?)
                """,
                (job_id, worker_id, int(row["attempts"]), ts),
            )
            conn.commit()

            if pre_status_hook is not None:
                pre_status_hook()

            conn.execute(
                """
                UPDATE jobs
                SET status = 'COMPLETED', lease_owner = NULL, lease_expires_at = NULL,
                    last_error = NULL, updated_at = ?
                WHERE job_id = ?
                """,
                (ts, job_id),
            )
            conn.commit()
            updated = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            return self._row_to_job(updated)
        finally:
            conn.close()

    def fail_job(
        self,
        job_id: str,
        worker_id: str,
        error_msg: str,
        backoff_seconds: float = 0.0,
        now: Optional[float] = None,
    ) -> Job:
        """BROKEN: Leaves job in RUNNING without routing to DLQ or releasing lease."""
        ts = float(time.time() if now is None else now)
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            if row is None:
                raise LeaseError(f"Unknown job: {job_id}")
            conn.execute(
                """
                UPDATE jobs SET last_error = ?, updated_at = ? WHERE job_id = ?
                """,
                (error_msg, ts, job_id),
            )
            conn.commit()
            updated = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            return self._row_to_job(updated)
        finally:
            conn.close()

    def reclaim_expired_leases(self, now: Optional[float] = None) -> int:
        """BROKEN: Does not reclaim expired RUNNING leases."""
        return 0

    def get_job(self, job_id: str) -> Optional[Job]:
        conn = self._connect()
        try:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            return self._row_to_job(row) if row is not None else None
        finally:
            conn.close()

    def list_jobs(self, status: Optional[Union[JobStatus, str]] = None) -> List[Job]:
        conn = self._connect()
        try:
            if status is not None:
                st = status.value if isinstance(status, JobStatus) else str(status)
                rows = conn.execute(
                    "SELECT * FROM jobs WHERE status = ? ORDER BY created_at ASC, rowid ASC",
                    (st,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM jobs ORDER BY created_at ASC, rowid ASC"
                ).fetchall()
            return [self._row_to_job(r) for r in rows]
        finally:
            conn.close()

    def get_audit_log(self, job_id: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            if job_id is not None:
                rows = conn.execute(
                    "SELECT * FROM job_audit_log WHERE job_id = ? ORDER BY id ASC",
                    (job_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM job_audit_log ORDER BY id ASC"
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def next_available_at(self) -> Optional[float]:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT MIN(available_at) AS next_ts FROM jobs WHERE status = 'PENDING'"
            ).fetchone()
            return float(row["next_ts"]) if row and row["next_ts"] is not None else None
        finally:
            conn.close()
