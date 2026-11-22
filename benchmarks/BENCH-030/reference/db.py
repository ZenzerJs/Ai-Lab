"""MVCC database orchestrating transactions, timestamps and GC."""
import threading
from collector import collect
from locks import LockTable
from txn import Transaction
from versions import VersionChain


class DB:
    """Snapshot-isolated key-value store.

    `ts` is the commit counter; each transaction snapshots at begin
    time and sees only versions committed at or before it.
    """

    def __init__(self):
        self.chains = {}
        self.locks = LockTable()
        self.ts = 0
        self.open_snapshots = {}    # txn_id -> snapshot_ts
        # serializes snapshot capture (begin) against commit publish:
        # a snapshot must never observe a half-installed commit
        self.commit_lock = threading.Lock()

    def next_ts(self) -> int:
        self.ts += 1
        return self.ts

    def _chain(self, key) -> VersionChain:
        return self.chains.setdefault(key, VersionChain())

    def begin(self, txn_id: str) -> Transaction:
        with self.commit_lock:
            txn = Transaction(self, txn_id, self.ts)
            self.open_snapshots[txn_id] = txn.snapshot_ts
            return txn

    def end(self, txn: Transaction) -> None:
        self.open_snapshots.pop(txn.id, None)

    def gc(self) -> int:
        """Collect garbage across all chains; returns versions dropped."""
        oldest = min(self.open_snapshots.values()) \
            if self.open_snapshots else self.ts
        return sum(collect(c, oldest) for c in self.chains.values())
