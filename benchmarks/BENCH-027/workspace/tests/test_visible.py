"""Visible smoke tests for BENCH-027 (not the full spec)."""
from chunker import chunk
from merkle import MerkleTree
from replica import Replica


def test_chunk_basic():
    assert chunk(b"abcdef", 4) == [b"abcd", b"ef"]


def test_merkle_two_leaves():
    tree = MerkleTree([b"x", b"y"])
    assert tree.root is not None


def test_sync_converges():
    a = Replica("a", b"hello world", chunk_size=4)
    b = Replica("b", b"hello WORLD", chunk_size=4)
    b.sync_with(a)
    assert a.is_consistent(b)
