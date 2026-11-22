"""Type-dispatched idempotent CRDT merge."""
from counters import GCounter, PNCounter
from lww import LWWRegister
from orset import ORSet
from vclock import VectorClock


def merge(a, b):
    """Merge two CRDTs of the same type.

    Merge is commutative, associative and idempotent: merge(a, a) == a.
    Raises TypeError for mismatched or unsupported types.
    """
    if type(a) is not type(b):
        raise TypeError(f"cannot merge {type(a).__name__} "
                        f"with {type(b).__name__}")
    if not isinstance(a, (VectorClock, GCounter, PNCounter,
                          ORSet, LWWRegister)):
        raise TypeError(f"unsupported CRDT type {type(a).__name__}")
    return a.merge(b)
