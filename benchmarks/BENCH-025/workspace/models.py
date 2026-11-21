"""Expression language models."""
from dataclasses import dataclass


class LexError(ValueError):
    pass


class ParseError(ValueError):
    pass


class EvalError(ValueError):
    pass


@dataclass(frozen=True)
class Token:
    kind: str
    text: str
    pos: int


@dataclass(frozen=True)
class Literal:
    value: int


@dataclass(frozen=True)
class Name:
    ident: str


@dataclass(frozen=True)
class Unary:
    op: str
    operand: object


@dataclass(frozen=True)
class Binary:
    op: str
    left: object
    right: object


@dataclass(frozen=True)
class Assign:
    ident: str
    value: object
