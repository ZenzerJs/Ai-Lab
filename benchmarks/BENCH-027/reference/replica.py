"""Replica holding chunked content that syncs toward a peer."""
from chunker import chunk
from merkle import MerkleTree
from sync import apply_plan, plan_repair


class Replica:
    """A replica of one document: deterministic chunks + Merkle state."""

    def __init__(self, name: str, data: bytes, chunk_size: int = 64):
        self.name = name
        self.chunk_size = chunk_size
        self.chunks = chunk(data, chunk_size)
        self.tree = MerkleTree(self.chunks)

    @property
    def root(self):
        return self.tree.root

    def is_consistent(self, peer: "Replica") -> bool:
        """True when both replicas' Merkle roots match."""
        return self.root == peer.root

    def sync_with(self, peer: "Replica") -> int:
        """Pull-repair this replica so it converges to `peer`'s content.

        Diffs local tree against peer's, fetches the differing chunk
        ranges from peer, rewrites local chunks, and rebuilds the tree.
        Returns the number of chunks repaired; peer is never mutated.
        Sync is idempotent: a second call repairs zero chunks.
        """
        plan = plan_repair(self.tree, peer.tree)
        repaired = sum(e - s for _o, s, e in plan)
        self.chunks = apply_plan(self.chunks, peer.chunks, plan)
        self.tree = MerkleTree(self.chunks)
        return repaired
