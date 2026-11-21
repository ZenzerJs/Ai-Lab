"""Recursive-descent parser for the filter grammar."""
import re

from ast_nodes import OPS, And, Comparison, Field, Literal, Not, Or

_NAME_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
_KEYWORDS = ("AND", "OR", "NOT", "like")


def _tokenize(text):
    tokens = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
        elif ch in "()":
            tokens.append(ch)
            i += 1
        elif text.startswith(("<=", ">=", "!="), i):
            tokens.append(text[i:i + 2])
            i += 2
        elif ch in "=<>":
            tokens.append(ch)
            i += 1
        elif ch == "'":
            i += 1
            buf = []
            while i < n and text[i] != "'":
                if text[i] == "\\":
                    i += 1
                    if i >= n:
                        raise ValueError("unterminated string literal")
                buf.append(text[i])
                i += 1
            if i >= n:
                raise ValueError("unterminated string literal")
            i += 1
            tokens.append(("str", "".join(buf)))
        elif match := _NAME_RE.match(text, i):
            word = match.group(0)
            tokens.append(word if word in _KEYWORDS else ("name", word))
            i = match.end()
        elif match := _NUM_RE.match(text, i):
            raw = match.group(0)
            tokens.append(("num", float(raw) if "." in raw else int(raw)))
            i = match.end()
        else:
            raise ValueError(f"unexpected character: {ch!r}")
    return tokens


def parse(text):
    tokens = _tokenize(text)
    node, pos = _parse_expr(tokens, 0)
    if pos != len(tokens):
        raise ValueError("unexpected trailing tokens")
    return node


def _parse_expr(tokens, pos):
    node, pos = _parse_not(tokens, pos)
    while pos < len(tokens) and tokens[pos] in ("AND", "OR"):
        joiner = tokens[pos]
        rhs, pos = _parse_not(tokens, pos + 1)
        node = And((node, rhs)) if joiner == "AND" else Or((node, rhs))
    return node, pos


def _parse_not(tokens, pos):
    if pos < len(tokens) and tokens[pos] == "NOT":
        node, pos = _parse_not(tokens, pos + 1)
        return Not(node), pos
    return _parse_primary(tokens, pos)


def _parse_primary(tokens, pos):
    if pos < len(tokens) and tokens[pos] == "(":
        node, pos = _parse_expr(tokens, pos + 1)
        if pos >= len(tokens) or tokens[pos] != ")":
            raise ValueError("missing closing parenthesis")
        return node, pos + 1
    return _parse_comparison(tokens, pos)


def _parse_comparison(tokens, pos):
    if pos + 3 > len(tokens):
        raise ValueError("incomplete comparison")
    name, op, lit = tokens[pos], tokens[pos + 1], tokens[pos + 2]
    if not (isinstance(name, tuple) and name[0] == "name"):
        raise ValueError("expected field name")
    if op not in OPS:
        raise ValueError("unsupported operator")
    if not (isinstance(lit, tuple) and lit[0] in ("str", "num")):
        raise ValueError("expected literal")
    return Comparison(Field(name[1]), op, Literal(lit[1])), pos + 3
