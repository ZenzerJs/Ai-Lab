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
    for i in range(n):
        if a[i] != b[i]:
            ranges.append((i, i + 1))
    if len(a) != len(b):
        lo = max(len(a), len(b))
        ranges.append((n, lo))
    return ranges
