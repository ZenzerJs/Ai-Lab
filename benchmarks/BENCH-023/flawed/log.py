"""Replicated log: indexed entries with conflict truncation."""
from models import ConsistencyError, LogEntry


class ReplicatedLog:
    def __init__(self):
        self.entries = []          # 1-indexed logically; index = pos + 1

    @property
    def last_index(self):
        return len(self.entries)

    @property
    def last_term(self):
        return self.entries[-1].term if self.entries else 0

    def at(self, index):
        """1-based entry access; index 0 is the sentinel before the log."""
        if index <= 0:
            return None
        if index > len(self.entries):
            return None
        return self.entries[index - 1]

    def term_at(self, index):
        entry = self.at(index)
        return entry.term if entry else 0

    def match(self, prev_index, prev_term):
        """True when the entry at prev_index has prev_term."""
        return self.term_at(prev_index) == prev_term

    def append_from(self, prev_index, entries, committed_index=0):
        """Append entries after prev_index, truncating any conflicting
        suffix. Committed entries are never truncated."""
        for i, entry in enumerate(entries):
            index = prev_index + 1 + i
            if index <= len(self.entries):
                if self.entries[index - 1].term == entry.term:
                    continue          # identical position; keep
                if index <= committed_index:
                    raise ConsistencyError(
                        f"truncate would drop committed index {index}")
                self.entries = self.entries[:index - 1]
            self.entries.append(entry)

    def up_to_date(self, last_index, last_term):
        """True when (last_term, last_index) is at least as fresh as ours.

        Raft freshness compares last_log_term first, then last_log_index.
        """
        if last_term != self.last_term:
            return last_term > self.last_term
        return last_index >= self.last_index
