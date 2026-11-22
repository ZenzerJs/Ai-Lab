"""Observed-Remove Set: add-wins semantics via unique add tags."""


class ORSet:
    """Set where each add carries a unique tag; remove tombstones only
    the tags it has observed, so a concurrent add always survives."""

    def __init__(self, adds=None, removes=None):
        self.adds = {el: set(tags) for el, tags in (adds or {}).items()}
        self.removes = set(removes or set())

    def add(self, element, tag: str) -> "ORSet":
        """Return a new set with `tag` recorded for `element`."""
        out = ORSet(self.adds, self.removes)
        out.adds.setdefault(element, set()).add(tag)
        return out

    def remove(self, element) -> "ORSet":
        """Tombstone every tag currently observed for `element`."""
        out = ORSet(self.adds, self.removes)
        out.removes |= out.adds.get(element, set())
        return out

    def contains(self, element) -> bool:
        return bool(self.adds.get(element, set()) - self.removes)

    def elements(self) -> list:
        """Sorted live elements."""
        return sorted(el for el in self.adds if self.contains(el))

    def merge(self, other: "ORSet") -> "ORSet":
        out = ORSet()
        for el in set(self.adds) | set(other.adds):
            out.adds[el] = (self.adds.get(el, set())
                            | other.adds.get(el, set()))
        out.removes = self.removes | other.removes
        return out
