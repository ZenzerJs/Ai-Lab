"""Versioned values for MVCC snapshot reads."""
from dataclasses import dataclass

TOMBSTONE = None
INF = float("inf")


@dataclass
class Version:
    """A committed version: visible for readers at begin_ts <= ts <
    end_ts. value is a str or the TOMBSTONE marker."""
    begin_ts: int
    end_ts: float
    value: object
    txn_id: str


class VersionChain:
    """Per-key versions, newest first."""

    def __init__(self):
        self.versions = []

    def add(self, version: Version) -> None:
        """Insert newest-first; the previous newest version closes at
        the new version's begin_ts."""
        if self.versions:
            self.versions[0].end_ts = version.begin_ts
        self.versions.insert(0, version)

    def latest(self):
        return self.versions[0] if self.versions else None

    def as_of(self, ts):
        """The version visible at timestamp ts, or None."""
        for v in self.versions:
            if v.begin_ts <= ts < v.end_ts:
                return v
        return None
