"""MVCC database orchestrating transactions and GC."""
from collector import collect
from locks import LockTable
from txn import Transaction
from versions import VersionChain


class DB:
    def __init__(self):
        self.chains = {}
        self.locks = LockTable()
        self.ts = 0
        self.open_snapshots = {}

    def next_ts(self):
        self.ts += 1
        return self.ts

    def _chain(self, key):
        return self.chains.setdefault(key, VersionChain())

    def begin(self, txn_id):
        txn = Transaction(self, txn_id, self.ts)
        self.open_snapshots[txn_id] = txn.snapshot_ts
        return txn

    def end(self, txn):
        self.open_snapshots.pop(txn.id, None)

    def gc(self):
        oldest = min(self.open_snapshots.values()) \
            if self.open_snapshots else self.ts
        return sum(collect(c, oldest) for c in self.chains.values())
