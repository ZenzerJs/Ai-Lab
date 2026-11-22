"""Public regex API over the compiled NFA."""
from compiler import compile as _compile
from matcher import run
from parser import parse


class Regex:
    """Compiled pattern; all matching is longest-match semantics."""

    def __init__(self, pattern: str):
        self.pattern = pattern
        self.nfa = _compile(parse(pattern))

    def match(self, text: str):
        """Longest anchored prefix match: returns end offset or None."""
        ends = run(self.nfa, text, 0)
        return ends[-1] if ends else None

    def search(self, text: str):
        """Leftmost-longest match anywhere: returns (start, end)|None."""
        for start in range(len(text) + 1):
            ends = run(self.nfa, text, start)
            if ends:
                return (start, ends[-1])
        return None

    def findall(self, text: str) -> list:
        """Non-overlapping leftmost-longest NON-EMPTY matches."""
        out = []
        pos = 0
        while pos < len(text):
            hit = self.search_at(text, pos)
            if hit is None:
                break
            start, end = hit
            out.append(text[start:end])
            pos = end if end > start else start + 1
        return out

    def search_at(self, text: str, pos: int):
        """Leftmost-longest match at-or-after pos; empty matches skipped
        only when a later non-empty match exists further right — the
        scan still prefers the earliest non-empty hit."""
        for start in range(pos, len(text) + 1):
            ends = run(self.nfa, text, start)
            non_empty = [e for e in ends if e > start]
            if non_empty:
                return (start, non_empty[0])   # shortest end
        return None
