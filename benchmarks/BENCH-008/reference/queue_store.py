"""
queue_store.py - Reference atomic SQLite QueueStore for BENCH-008.
"""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Callable, Dict, Iterator, List, Optional, Union

from models import Job, JobStatus, LeaseError, validate_transition


class QueueStore:
    """
    SQLite-backed job queue using BEGIN IMMEDIATE transactions for atomic lease
    claiming, single-transaction audit logging, and expired lease reclamation.
    """

    def __init__(self, db_path: Union[str, Path]) -> None:
        self.db_path = str(db_path)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

    @contextmanager
    def _write_tx(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            for attempt in range(50):
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    break
                except sqlite3.OperationalError as exc:
                    msg = str(exc).lower()
                    if ("locked" in msg or "busy" in msg) and attempt < 49:
                        time.sleep(0.002 * (attempt + 1))
                        continue
                    raise
            yield conn
            if conn.in_transaction:
                conn.execute("COMMIT")
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._write_tx() as conn:
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

    def _row_to_job(self, row: sqlite3.Row) -> Job:
        return Job(
            job_id=row["job_id"],
            payload=json.loads(row["payload_json"]),
            status=JobStatus(row["status"]),
            attempts=int(row["attempts"]),
            max_attempts=int(row["max_attempts"]),
            lease_owner=row["lease_owner"],
            lease_expires_at=(
                float(row["lease_expires_at"])
                if row["lease_expires_at"] is not None
                else None
            ),
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
        validated = Job(
            job_id=job_id,
            payload=payload,
            status=JobStatus.PENDING,
            attempts=0,
            max_attempts=max_attempts,
            available_at=float(available_at),
            created_at=ts,
            updated_at=ts,
        )
        with self._write_tx() as conn:
            conn.execute(
                """
                INSERT INTO jobs (
                    job_id, payload_json, status, attempts, max_attempts,
                    lease_owner, lease_expires_at, available_at, last_error,
                    created_at, updated_at
                ) VALUES (?, ?, ?, 0, ?, NULL, NULL, ?, NULL, ?, ?)
                """,
                (
                    validated.job_id,
                    json.dumps(validated.payload),
                    JobStatus.PENDING.value,
                    validated.max_attempts,
                    validated.available_at,
                    ts,
                    ts,
                ),
            )
            conn.execute(
                """
                INSERT INTO job_audit_log (job_id, event_type, worker_id, attempt, details, created_at)
                VALUES (?, 'ENQUEUED', NULL, 0, NULL, ?)
                """,
                (validated.job_id, ts),
            )
            row = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (validated.job_id,)
            ).fetchone()
            return self._row_to_job(row)

    def _reclaim_expired_in_tx(self, conn: sqlite3.Connection, ts: float) -> int:
        expired_rows = conn.execute(
            """
            SELECT job_id, attempts, max_attempts FROM jobs
            WHERE status = 'RUNNING'
              AND lease_expires_at IS NOT NULL
              AND lease_expires_at <= ?
            """,
            (ts,),
        ).fetchall()
        reclaimed = 0
        for row in expired_rows:
            attempts = int(row["attempts"])
            max_attempts = int(row["max_attempts"])
            if attempts >= max_attempts:
                next_status = JobStatus.DLQ
                event_type = "DEAD_LETTERED"
                reason = "lease_expired_max_attempts"
            else:
                next_status = JobStatus.PENDING
                event_type = "LEASE_EXPIRED"
                reason = "lease_expired"

            validate_transition(JobStatus.RUNNING, next_status)
            cur = conn.execute(
                """
                UPDATE jobs
                SET status = ?, lease_owner = NULL, lease_expires_at = NULL,
                    available_at = ?, last_error = ?, updated_at = ?
                WHERE job_id = ? AND status = 'RUNNING'
                """,
                (next_status.value, ts, reason, ts, row["job_id"]),
            )
            if cur.rowcount == 1:
                conn.execute(
                    """
                    INSERT INTO job_audit_log (job_id, event_type, worker_id, attempt, details, created_at)
                    VALUES (?, ?, NULL, ?, ?, ?)
                    """,
                    (row["job_id"], event_type, attempts, reason, ts),
                )
                reclaimed += 1
        return reclaimed

    def reclaim_expired_leases(self, now: Optional[float] = None) -> int:
        """Atomically reclaim expired RUNNING leases back to PENDING or DLQ."""
        ts = float(time.time() if now is None else now)
        with self._write_tx() as conn:
            return self._reclaim_expired_in_tx(conn, ts)

    def claim_next_job(
        self,
        worker_id: str,
        lease_ttl: float = 5.0,
        now: Optional[float] = None,
    ) -> Optional[Job]:
        """Atomically reclaim expired leases and claim the next ready PENDING job."""
        if not worker_id or not isinstance(worker_id, str):
            raise ValueError("worker_id must be a non-empty string")
        if lease_ttl <= 0:
            raise ValueError("lease_ttl must be > 0")

        ts = float(time.time() if now is None else now)
        with self._write_tx() as conn:
            self._reclaim_expired_in_tx(conn, ts)
            row = conn.execute(
                """
                SELECT * FROM jobs
                WHERE status = 'PENDING'
                  AND available_at <= ?
                  AND attempts < max_attempts
                ORDER BY created_at ASC, rowid ASC
                LIMIT 1
                """,
                (ts,),
            ).fetchone()
            if row is None:
                return None

            validate_transition(JobStatus.PENDING, JobStatus.RUNNING)
            new_attempts = int(row["attempts"]) + 1
            lease_expires_at = ts + float(lease_ttl)
            cur = conn.execute(
                """
                UPDATE jobs
                SET status = 'RUNNING', attempts = ?, lease_owner = ?,
                    lease_expires_at = ?, updated_at = ?
                WHERE job_id = ? AND status = 'PENDING'
                """,
                (new_attempts, worker_id, lease_expires_at, ts, row["job_id"]),
            )
            if cur.rowcount != 1:
                return None

            conn.execute(
                """
                INSERT INTO job_audit_log (job_id, event_type, worker_id, attempt, details, created_at)
                VALUES (?, 'CLAIMED', ?, ?, NULL, ?)
                """,
                (row["job_id"], worker_id, new_attempts, ts),
            )
            updated = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (row["job_id"],)
            ).fetchone()
            return self._row_to_job(updated)

    def complete_job(
        self,
        job_id: str,
        worker_id: str,
        now: Optional[float] = None,
        pre_status_hook: Optional[Callable[[], None]] = None,
    ) -> Job:
        """
        Atomically mark a RUNNING job COMPLETED and insert audit record in one transaction.
        Rolls back completely if lease ownership fails or pre_status_hook raises.
        """
        ts = float(time.time() if now is None else now)
        with self._write_tx() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            if row is None:
                raise LeaseError(f"Unknown job: {job_id}")
            if row["status"] != JobStatus.RUNNING.value or row["lease_owner"] != worker_id:
                raise LeaseError(
                    f"Lease mismatch for job {job_id}: status={row['status']}, owner={row['lease_owner']}"
                )

            validate_transition(JobStatus.RUNNING, JobStatus.COMPLETED)

            if pre_status_hook is not None:
                pre_status_hook()

            cur = conn.execute(
                """
                UPDATE jobs
                SET status = 'COMPLETED', lease_owner = NULL, lease_expires_at = NULL,
                    last_error = NULL, updated_at = ?
                WHERE job_id = ? AND status = 'RUNNING' AND lease_owner = ?
                """,
                (ts, job_id, worker_id),
            )
            if cur.rowcount != 1:
                raise LeaseError(f"Failed to update lease-owned job {job_id}")

            conn.execute(
                """
                INSERT INTO job_audit_log (job_id, event_type, worker_id, attempt, details, created_at)
                VALUES (?, 'COMPLETED', ?, ?, NULL, ?)
                """,
                (job_id, worker_id, int(row["attempts"]), ts),
            )
            updated = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            return self._row_to_job(updated)

    def fail_job(
        self,
        job_id: str,
        worker_id: str,
        error_msg: str,
        backoff_seconds: float = 0.0,
        now: Optional[float] = None,
    ) -> Job:
        """
        Atomically release lease and return job to PENDING (or DLQ after max_attempts)
        alongside a single-transaction audit log entry.
        """
        ts = float(time.time() if now is None else now)
        with self._write_tx() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            if row is None:
                raise LeaseError(f"Unknown job: {job_id}")
            if row["status"] != JobStatus.RUNNING.value or row["lease_owner"] != worker_id:
                raise LeaseError(
                    f"Lease mismatch for job {job_id}: status={row['status']}, owner={row['lease_owner']}"
                )

            attempts = int(row["attempts"])
            max_attempts = int(row["max_attempts"])
            if attempts >= max_attempts:
                next_status = JobStatus.DLQ
                event_type = "DEAD_LETTERED"
                next_avail = ts
            else:
                next_status = JobStatus.PENDING
                event_type = "RETRY_SCHEDULED"
                next_avail = ts + max(0.0, float(backoff_seconds))

            validate_transition(JobStatus.RUNNING, next_status)
            cur = conn.execute(
                """
                UPDATE jobs
                SET status = ?, lease_owner = NULL, lease_expires_at = NULL,
                    available_at = ?, last_error = ?, updated_at = ?
                WHERE job_id = ? AND status = 'RUNNING' AND lease_owner = ?
                """,
                (next_status.value, next_avail, error_msg, ts, job_id, worker_id),
            )
            if cur.rowcount != 1:
                raise LeaseError(f"Failed to fail lease-owned job {job_id}")

            conn.execute(
                """
                INSERT INTO job_audit_log (job_id, event_type, worker_id, attempt, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (job_id, event_type, worker_id, attempts, error_msg, ts),
            )
            updated = conn.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
            return self._row_to_job(updated)

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
