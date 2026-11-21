"""ETL record types and deterministic summary metrics."""
from dataclasses import dataclass


def _check_line_no(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("line_no must be a positive integer")


@dataclass(frozen=True)
class RawRecord:
    line_no: int
    data: object = None
    error: str = None

    def __post_init__(self):
        _check_line_no(self.line_no)
        if self.error is not None and not isinstance(self.error, str):
            raise ValueError("error must be a string")


@dataclass(frozen=True)
class DeadLetter:
    line_no: int
    error: str
    raw: object

    def __post_init__(self):
        _check_line_no(self.line_no)
        if not isinstance(self.error, str) or not self.error:
            raise ValueError("error must be a nonempty string")


@dataclass(frozen=True)
class Summary:
    total: int
    processed: int
    dead_lettered: int

    def __post_init__(self):
        for name in ("total", "processed", "dead_lettered"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        if self.total != self.processed + self.dead_lettered:
            raise ValueError("total must equal processed + dead_lettered")


@dataclass(frozen=True)
class PipelineResult:
    rows: tuple
    dead_letters: tuple
    summary: Summary

    def __post_init__(self):
        rows = tuple(self.rows)
        dead = tuple(self.dead_letters)
        object.__setattr__(self, "rows", rows)
        object.__setattr__(self, "dead_letters", dead)
        if not isinstance(self.summary, Summary):
            raise ValueError("summary must be a Summary")
        if (self.summary.processed, self.summary.dead_lettered) != (len(rows), len(dead)):
            raise ValueError("summary counts must match rows and dead_letters")
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("rows must contain dicts")
        for letter in dead:
            if not isinstance(letter, DeadLetter):
                raise ValueError("dead_letters must contain DeadLetter")
