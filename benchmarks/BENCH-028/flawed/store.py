"""Replicated key->CRDT store converging via peer merge."""
from merge import merge
from vclock import VectorClock


class Store:
    """Holds named CRDTs plus the replica's vector clock."""

    def __init__(self, node_id: str, data=None, clock=None):
        self.node_id = node_id
        self.data = dict(data or {})
        self.clock = clock if clock is not None else VectorClock()

    def apply(self, key: str, crdt) -> "Store":
        """Record `crdt` under `key` and advance this replica's clock."""
        out = Store(self.node_id, self.data, self.clock)
        out.data[key] = crdt
        out.clock = out.clock.increment(self.node_id)
        return out

    def get(self, key: str):
        return self.data.get(key)

    def merge_peer(self, peer: "Store") -> "Store":
        """Merge every key of both stores and both clocks.

        Keys present on one side only are carried over unchanged;
        merging twice is a no-op (idempotent convergence).
        """
        out = Store(self.node_id)
        for key in set(self.data) | set(peer.data):
            if key in self.data and key in peer.data:
                out.data[key] = merge(self.data[key], peer.data[key])
            else:
                out.data[key] = self.data.get(key, peer.data.get(key))
        out.clock = self.clock.merge(peer.clock)
        return out
