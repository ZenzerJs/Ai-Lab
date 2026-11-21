"""Filter AST node definitions."""
from dataclasses import dataclass

OPS = ("=", "!=", "<", "<=", ">", ">=", "like")


@dataclass(frozen=True)
class Field:
    name: str


@dataclass(frozen=True)
class Literal:
    value: object


@dataclass(frozen=True)
class Comparison:
    field: Field
    op: str
    literal: Literal


@dataclass(frozen=True)
class And:
    children: tuple


@dataclass(frozen=True)
class Or:
    children: tuple


@dataclass(frozen=True)
class Not:
    child: object
