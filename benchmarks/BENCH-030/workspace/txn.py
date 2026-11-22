"""Transactions under snapshot isolation."""
from versions import TOMBSTONE, Version, INF
from rwset import ReadWriteSet


class ConflictError(RuntimeError):
    pass


class Transaction:
    def __init__(self, db, txn_id, snapshot_ts):
        self.db = db
        self.id = txn_id
        self.snapshot_ts = snapshot_ts
        self.rwset = ReadWriteSet()
        self.state = "open"

    def read(self, key):
        if key in self.rwset.writes:
            return self.rwset.writes[key]
        v = self.db._chain(key).latest()   # ignores the snapshot
        self.rwset.add_read(key, v)
        return None if v is None else v.value

    def write(self, key, value):
        self.rwset.add_write(key, value)

    def commit(self):
        if self.state != "open":
            raise ConflictError(f"txn {self.id} is {self.state}")
        # No conflict check and no write locks.
        for key, value in self.rwset.writes.items():
            self.db._chain(key).add(
                Version(self.db.next_ts(), INF, value, self.id))
        self.state = "committed"
        self.db.end(self)
        return self.db.ts

    def abort(self):
        self.state = "aborted"
        self.db.end(self)
