"""Replicated log."""
from models import LogEntry


class ReplicatedLog:
    def __init__(self):
        self.entries = []

    @property
    def last_index(self):
        return len(self.entries)

    @property
    def last_term(self):
        return self.entries[-1].term if self.entries else 0

    def at(self, index):
        if index == 0 or index > len(self.entries):
            return None
        return self.entries[index - 1]

    def term_at(self, index):
        entry = self.at(index)
        return entry.term if entry else 0

    def match(self, prev_index, prev_term):
        return self.term_at(prev_index) == prev_term

    def append_from(self, prev_index, entries, committed_index=0):
        for i, entry in enumerate(entries):
            index = prev_index + 1 + i
            if index <= len(self.entries):
                if self.entries[index - 1].term == entry.term:
                    continue
                self.entries = self.entries[:index - 1]
            self.entries.append(entry)

    def up_to_date(self, last_index, last_term):
        return True
