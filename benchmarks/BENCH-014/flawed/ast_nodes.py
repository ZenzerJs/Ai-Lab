"""Filter AST node definitions."""
import math
import re
from dataclasses import dataclass

_FIELD_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
OPS = ("=", "!=", "<", "<=", ">", ">=", "like")


@dataclass(frozen=True)
class Field:
    name: str

    def __post_init__(self):
        if not isinstance(self.name, str) or not _FIELD_RE.fullmatch(self.name):
            raise ValueError("invalid field name")


@dataclass(frozen=True)
class Literal:
    value: object

    def __post_init__(self):
        if isinstance(self.value, bool) or not isinstance(self.value, (str, int, float)):
            raise ValueError("unsupported literal type")
        if isinstance(self.value, float) and not math.isfinite(self.value):
            raise ValueError("non-finite literal")


@dataclass(frozen=True)
class Comparison:
    field: Field
    op: str
    literal: Literal

    def __post_init__(self):
        if not isinstance(self.field, Field) or not isinstance(self.literal, Literal):
            raise ValueError("comparison requires Field and Literal")
        if self.op not in OPS:
            raise ValueError("unsupported operator")
        if self.op == "like" and not isinstance(self.literal.value, str):
            raise ValueError("like requires a string literal")
        if self.op in ("<", "<=", ">", ">=") and isinstance(self.literal.value, str):
            raise ValueError("ordering operators require numeric literals")


def _check_node(node):
    if not isinstance(node, (Comparison, And, Or, Not)):
        raise ValueError("expected filter node")


@dataclass(frozen=True)
class And:
    children: tuple

    def __post_init__(self):
        children = tuple(self.children)
        if not children:
            raise ValueError("empty conjunction")
        for child in children:
            _check_node(child)
        object.__setattr__(self, "children", children)


@dataclass(frozen=True)
class Or:
    children: tuple

    def __post_init__(self):
        children = tuple(self.children)
        if not children:
            raise ValueError("empty disjunction")
        for child in children:
            _check_node(child)
        object.__setattr__(self, "children", children)


@dataclass(frozen=True)
class Not:
    child: object

    def __post_init__(self):
        _check_node(self.child)
