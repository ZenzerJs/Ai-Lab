"""B+Tree node types: leaves hold entries; internals hold separators."""
import bisect


class LeafNode:
    is_leaf = True

    def __init__(self, keys=None, values=None):
        self.keys = list(keys or [])
        self.values = list(values or [])
        self.next = None  # right sibling leaf

    def insert(self, key, value):
        pos = bisect.bisect_left(self.keys, key)
        self.keys.insert(pos, key)
        self.values.insert(pos, value)

    def remove(self, key):
        pos = bisect.bisect_left(self.keys, key)
        if pos >= len(self.keys) or self.keys[pos] != key:
            raise KeyError(key)
        self.keys.pop(pos)
        self.values.pop(pos)

    def split(self):
        """Split an overflowing leaf. Returns (right_node, pushed_key).

        Left keeps keys[:mid]; right gets keys[mid:]; the right node's
        first key is copied up as the separator (it stays in the leaf).
        """
        mid = len(self.keys) // 2
        right = LeafNode(self.keys[mid:], self.values[mid:])
        right.next = self.next
        self.keys = self.keys[:mid]
        self.values = self.values[:mid]
        self.next = right
        return right, right.keys[0]


class InternalNode:
    is_leaf = False

    def __init__(self, keys=None, children=None):
        self.keys = list(keys or [])       # separators; keys[i] = smallest key of children[i+1]
        self.children = list(children or [])

    def split(self):
        """Split an overflowing internal node. Returns (right_node, promoted_key).

        The middle separator is moved up (not copied): left keeps
        keys[:mid] and children[:mid+1]; right gets keys[mid+1:] and
        children[mid+1:].
        """
        mid = len(self.keys) // 2
        promoted = self.keys[mid]
        right = InternalNode(self.keys[mid + 1:], self.children[mid + 1:])
        self.keys = self.keys[:mid]
        self.children = self.children[:mid + 1]
        return right, promoted
