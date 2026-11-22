"""Visible smoke tests for BENCH-029 (not the full spec)."""
from engine import Regex
from parser import parse


def test_literal_match():
    assert Regex("abc").match("abcdef") == 3


def test_parse_alt():
    tree = parse("a|b")
    assert tree.left.c == "a" and tree.right.c == "b"


def test_search():
    assert Regex("bc").search("abc") == (1, 3)
