"""Replicated key->CRDT store."""
from merge import merge
from vclock import VectorClock


class Store:
    def __init__(self, node_id, data=None, clock=None):
        self.node_id = node_id
        self.data = dict(data or {})
        self.clock = clock if clock is not None else VectorClock()

    def apply(self, key, crdt):
        out = Store(self.node_id, self.data, self.clock)
        out.data[key] = crdt
        out.clock = out.clock.increment(self.node_id)
        return out

    def get(self, key):
        return self.data.get(key)

    def merge_peer(self, peer):
        out = Store(self.node_id)
        for key in set(self.data) | set(peer.data):
            out.data[key] = peer.data.get(key, self.data.get(key))
        out.clock = self.clock.merge(peer.clock)
        return out
