"""AST node types for the regex language."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Char:
    c: str


@dataclass(frozen=True)
class Any:
    pass


@dataclass(frozen=True)
class Class:
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
