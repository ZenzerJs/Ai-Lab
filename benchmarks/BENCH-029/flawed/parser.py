"""Recursive-descent parser: pattern string -> AST.

Grammar (loosest to tightest):
    alt    := concat ('|' concat)*
    concat := repeat+
    repeat := atom ('*' | '+' | '?')*
    atom   := '(' alt ')' | '.' | '[' class ']' | '\\' escape | literal
"""
from syntax import Alt, Any, Char, Class, Concat, Opt, Plus, Star


class ParseError(ValueError):
    pass


_ESCAPES = {"n": "\n", "t": "\t", "d": None, "w": None, "s": None}
_CLASS_ESCAPES = {
    "d": (("0", "9"),),
    "w": (("0", "9"), ("A", "Z"), ("_", "_"), ("a", "z")),
    "s": ((" ", " "), ("\t", "\t"), ("\n", "\n")),
}


def parse(pattern: str):
    nodes, pos = _alt(pattern, 0)
    if pos != len(pattern):
        raise ParseError(f"unexpected '{pattern[pos]}' at {pos}")
    return nodes


def _alt(pat, pos):
    node, pos = _concat(pat, pos)
    while pos < len(pat) and pat[pos] == "|":
        rhs, pos = _concat(pat, pos + 1)
        node = Alt(node, rhs)
    return node, pos


def _concat(pat, pos):
    nodes = []
    while pos < len(pat) and pat[pos] not in ")|":
        node, pos = _repeat(pat, pos)
        nodes.append(node)
    if not nodes:
        raise ParseError("empty alternation branch")
    node = nodes[0]
    for nxt in nodes[1:]:
        node = Concat(node, nxt)
    return node, pos


def _repeat(pat, pos):
    node, pos = _atom(pat, pos)
    while pos < len(pat) and pat[pos] in "*+?":
        kind = pat[pos]
        pos += 1
        node = {"*": Star, "+": Plus, "?": Opt}[kind](node)
    return node, pos


def _atom(pat, pos):
    ch = pat[pos]
    if ch == "(":
        node, pos = _alt(pat, pos + 1)
        if pos >= len(pat) or pat[pos] != ")":
            raise ParseError("unclosed group")
        return node, pos + 1
    if ch == ".":
        return Any(), pos + 1
    if ch == "[":
        return _class(pat, pos + 1)
    if ch == "\\":
        if pos + 1 >= len(pat):
            raise ParseError("trailing backslash")
        esc = pat[pos + 1]
        if esc in _CLASS_ESCAPES:
            return Class(False, _CLASS_ESCAPES[esc]), pos + 2
        return Char(_ESCAPES.get(esc, esc) or esc), pos + 2
    return Char(ch), pos + 1


def _class(pat, pos):
    negated = False
    if pos < len(pat) and pat[pos] == "^":
        negated = True
        pos += 1
    ranges = []
    while pos < len(pat) and pat[pos] != "]":
        if pat[pos] == "\\" and pos + 1 < len(pat) and \
                pat[pos + 1] in _CLASS_ESCAPES:
            ranges.extend(_CLASS_ESCAPES[pat[pos + 1]])
            pos += 2
            continue
        lo = pat[pos]
        if pos + 2 < len(pat) and pat[pos + 1] == "-" and \
                pat[pos + 2] != "]":
            ranges.append((lo, pat[pos + 2]))
            pos += 3
        else:
            ranges.append((lo, lo))
            pos += 1
    if pos >= len(pat):
        raise ParseError("unclosed class")
    if not ranges:
        raise ParseError("empty class")
    return Class(negated, tuple(ranges)), pos + 1
