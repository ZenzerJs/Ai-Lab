"""Public regex API over the compiled NFA."""
from compiler import compile as _compile
from matcher import run
from parser import parse


class Regex:
    def __init__(self, pattern):
        self.pattern = pattern
        self.nfa = _compile(parse(pattern))

    def match(self, text):
        ends = run(self.nfa, text, 0)
        return ends[-1] if ends else None

    def search(self, text):
        ends = run(self.nfa, text, 0)
        if ends:
            return (0, ends[-1])
        return None

    def findall(self, text):
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

    def search_at(self, text, pos):
        for start in range(pos, len(text) + 1):
            ends = run(self.nfa, text, start)
            if ends:
                return (start, ends[0])   # shortest match
        return None
