"""Binary Merkle tree over chunk hashes."""
from hashing import leaf_hash, node_hash


class MerkleTree:
    def __init__(self, chunks):
        self.leaves = [leaf_hash(c) for c in chunks]
        level = list(self.leaves)
        self.levels = [level]
        while len(level) > 1:
            nxt = [node_hash(level[i], level[i + 1])
                   for i in range(0, len(level) - 1, 2)]
            if len(level) % 2 == 1:
                nxt.append(node_hash(level[-1], level[-1]))
            level = nxt
            self.levels.append(level)

    @property
    def root(self):
        return self.levels[-1][0] if self.leaves else None
