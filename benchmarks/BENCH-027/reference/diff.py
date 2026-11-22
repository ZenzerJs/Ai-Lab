"""Merkle-tree diffing: minimal leaf ranges whose hashes disagree."""
from merkle import MerkleTree


def diff_ranges(local: MerkleTree, remote: MerkleTree) -> list:
    """Minimal (start, end) leaf-index ranges that differ between trees.

    Equal roots short-circuit to []. Otherwise consecutive leaf
    positions whose hashes differ are grouped into half-open ranges.
    When leaf counts differ, the surplus tail positions on the longer
    side form one trailing range.
    """
    if local.root == remote.root:
        return []
    a, b = local.leaves, remote.leaves
    n = min(len(a), len(b))
    ranges = []
    i = 0
    while i < n:
        if a[i] == b[i]:
            i += 1
            continue
        start = i
        while i < n and a[i] != b[i]:
            i += 1
        ranges.append((start, i))
    if len(a) != len(b):
        lo = max(len(a), len(b))
        ranges.append((n, lo))
    return ranges
