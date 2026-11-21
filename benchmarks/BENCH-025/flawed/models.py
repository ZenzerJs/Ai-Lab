"""Expression language models: tokens, AST nodes, exceptions."""
from dataclasses import dataclass


class LexError(ValueError):
    """Unknown character or malformed token; carries 0-based offset."""


class ParseError(ValueError):
    """Unexpected token or truncated input; carries 0-based offset."""


class EvalError(ValueError):
    """Runtime error: undefined name, division by zero, arity."""


@dataclass(frozen=True)
class Token:
    kind: str        # "num", "name", "op", "lparen", "rparen", "semi", "eq"
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
