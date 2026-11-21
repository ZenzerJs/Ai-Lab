"""ETL record types and summary metrics."""
from dataclasses import dataclass


@dataclass(frozen=True)
class RawRecord:
    line_no: int
    data: object = None
    error: str = None


@dataclass(frozen=True)
class DeadLetter:
    line_no: int
    error: str
    raw: object


@dataclass(frozen=True)
class Summary:
    total: int
    processed: int
    dead_lettered: int


@dataclass(frozen=True)
class PipelineResult:
    rows: tuple
    dead_letters: tuple
    summary: Summary
