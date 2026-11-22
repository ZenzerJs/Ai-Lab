"""Binary Merkle tree over ordered chunk hashes with odd promotion."""
from hashing import leaf_hash, node_hash


class MerkleTree:
    """Merkle tree built over an ordered list of data chunks.

    Leaves are the leaf_hash of each chunk. Each level pairs adjacent
    nodes with node_hash(left, right); a lone leftover node is promoted
    unchanged to the next level. `root` is the top hash, or None for an
    empty chunk list.
    """

    def __init__(self, chunks):
        self.leaves = [leaf_hash(c) for c in chunks]
        level = list(self.leaves)
        self.levels = [level]
        while len(level) > 1:
            nxt = [node_hash(level[i], level[i + 1])
                   for i in range(0, len(level) - 1, 2)]
            if len(level) % 2 == 1:
                nxt.append(level[-1])
            level = nxt
            self.levels.append(level)

    @property
    def root(self):
        return self.levels[-1][0] if self.leaves else None
