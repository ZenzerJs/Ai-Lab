"""Transactions under snapshot isolation, first-committer-wins."""
from versions import TOMBSTONE, Version, INF
from rwset import ReadWriteSet


class ConflictError(RuntimeError):
    """Raised on commit when a written key advanced past my snapshot."""


class Transaction:
    """Reads at a fixed snapshot_ts; writes buffered until commit."""

    def __init__(self, db, txn_id: str, snapshot_ts: int):
        self.db = db
        self.id = txn_id
        self.snapshot_ts = snapshot_ts
        self.rwset = ReadWriteSet()
        self.state = "open"    # open | committed | aborted

    def read(self, key):
        """Own writes first, then the version visible at snapshot_ts;
        tombstones read as None."""
        if key in self.rwset.writes:
            val = self.rwset.writes[key]
            return val
        v = self.db._chain(key).as_of(self.snapshot_ts)
        self.rwset.add_read(key, v)
        return None if v is None or v.value is TOMBSTONE else v.value

    def write(self, key, value) -> None:
        """Buffer a write; value None marks a delete tombstone."""
        self.rwset.add_write(key, value)

    def commit(self):
        """First-committer-wins commit.

        Acquires each written key's lock; aborts with ConflictError when
        a key's newest committed version is newer than my snapshot.
        Committed versions are stamped with one commit_ts.
        """
        if self.state != "open":
            raise ConflictError(f"txn {self.id} is {self.state}")
        held = []
        try:
            for key in self.rwset.writes:
                if not self.db.locks.acquire(key, self.id):
                    raise ConflictError(f"key {key} locked by another txn")
                held.append(key)
            for key in self.rwset.writes:
                latest = self.db._chain(key).latest()
                if latest is not None and \
                        latest.begin_ts >= self.snapshot_ts:
                    raise ConflictError(
                        f"key {key} committed at {latest.begin_ts} "
                        f"after snapshot {self.snapshot_ts}")
            # publish atomically against concurrent begin(): a new
            # snapshot either sees every version of this commit or none
            with self.db.commit_lock:
                commit_ts = self.db.next_ts()
                for key, value in self.rwset.writes.items():
                    self.db._chain(key).add(
                        Version(commit_ts, INF, value, self.id))
            self.state = "committed"
            self.db.end(self)
            return commit_ts
        except ConflictError:
            self.abort()
            raise
        finally:
            for key in held:
                self.db.locks.release(key, self.id)

    def abort(self) -> None:
        for key in self.rwset.writes:
            self.db.locks.release(key, self.id)
        self.state = "aborted"
        self.db.end(self)
