"""Observed-Remove Set with tagged adds."""


class ORSet:
    def __init__(self, adds=None, removes=None):
        self.adds = {el: set(tags) for el, tags in (adds or {}).items()}
        self.removes = set(removes or set())

    def add(self, element, tag):
        out = ORSet(self.adds, self.removes)
        out.adds.setdefault(element, set()).add(tag)
        return out

    def remove(self, element):
        out = ORSet(self.adds, self.removes)
        out.removes.add(element)   # tombstone the element itself
        return out

    def contains(self, element):
        return element in self.adds and element not in self.removes

    def elements(self):
        return sorted(el for el in self.adds if self.contains(el))

    def merge(self, other):
        out = ORSet()
        for el in set(self.adds) | set(other.adds):
            out.adds[el] = (self.adds.get(el, set())
                            | other.adds.get(el, set()))
        out.removes = self.removes | other.removes
        return out
