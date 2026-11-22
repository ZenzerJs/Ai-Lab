"""AST node types for the regex language."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Char:
    c: str


@dataclass(frozen=True)
class Any:
    """Any character except newline."""


@dataclass(frozen=True)
class Class:
    """Character class: negated flag + inclusive (lo, hi) ranges."""
    negated: bool
    ranges: tuple


@dataclass(frozen=True)
class Concat:
    left: object
    right: object


@dataclass(frozen=True)
class Alt:
    left: object
    right: object


@dataclass(frozen=True)
class Star:
    node: object


@dataclass(frozen=True)
class Plus:
    node: object


@dataclass(frozen=True)
class Opt:
    node: object
