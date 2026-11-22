"""Versioned values for MVCC reads."""
from dataclasses import dataclass

TOMBSTONE = None
INF = float("inf")


@dataclass
class Version:
    begin_ts: int
    end_ts: float
    value: object
    txn_id: str


class VersionChain:
    def __init__(self):
        self.versions = []

    def add(self, version):
        # Previous newest stays open-ended; chain ordered oldest-first.
        self.versions.append(version)

    def latest(self):
        return self.versions[-1] if self.versions else None

    def as_of(self, ts):
        for v in self.versions:
            if v.begin_ts <= ts < v.end_ts:
                return v
        return None
