"""Deterministic page store for B+Tree nodes.

Every node gets a stable page id ("L0", "I3"). Serialization produces a
deterministically ordered dict-of-dicts snapshot used by Index.persist().
"""


class PageStore:
    def __init__(self):
        self._pages = {}      # page_id -> serialized node dict
        self._counter = 0

    def allocate(self, node):
        prefix = "L" if node.is_leaf else "I"
        page_id = f"{prefix}{self._counter}"
        self._counter += 1
        self.write(page_id, node)
        return page_id

    def write(self, page_id, node):
        if node.is_leaf:
            self._pages[page_id] = {
                "kind": "leaf",
                "keys": list(node.keys),
                "values": list(node.values),
            }
        else:
            self._pages[page_id] = {
                "kind": "internal",
                "keys": list(node.keys),
            }

    def read(self, page_id):
        return self._pages[page_id]

    def dump(self):
        """Deterministic snapshot: page ids sorted by (kind, numeric id)."""
        def sort_key(pid):
            num = int(pid[1:])
            return (0 if pid[0] == "I" else 1, num)

        return {pid: self._pages[pid] for pid in sorted(self._pages, key=sort_key)}
