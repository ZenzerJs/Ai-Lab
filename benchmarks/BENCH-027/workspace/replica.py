"""Replica holding chunked content that syncs with a peer."""
from chunker import chunk
from merkle import MerkleTree
from sync import apply_plan, plan_repair


class Replica:
    def __init__(self, name, data, chunk_size=64):
        self.name = name
        self.chunk_size = chunk_size
        self.chunks = chunk(data, chunk_size)
        self.tree = MerkleTree(self.chunks)

    @property
    def root(self):
        return self.tree.root

    def is_consistent(self, peer):
        return self.root == peer.root

    def sync_with(self, peer):
        # Push local state into the peer.
        plan = plan_repair(peer.tree, self.tree)
        peer.chunks = apply_plan(peer.chunks, self.chunks, plan)
        peer.tree = MerkleTree(peer.chunks)
        return len(plan)
