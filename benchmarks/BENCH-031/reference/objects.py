"""Content-addressed objects: deterministic ids via sorted JSON."""
import copy
import hashlib
import json


def object_id(kind: str, payload) -> str:
    """Stable id: sha256 over canonical (sorted-key) JSON."""
    body = json.dumps({"kind": kind, "payload": payload},
                      sort_keys=True)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


class ObjectStore:
    """oid -> (kind, payload) map; put is idempotent."""

    def __init__(self):
        self.objects = {}

    def put(self, kind: str, payload) -> str:
        oid = object_id(kind, payload)
        # deep-copy: content addresses only hold when the stored
        # payload can't be mutated through the caller's reference
        self.objects[oid] = (kind, copy.deepcopy(payload))
        return oid

    def get(self, oid: str):
        if oid not in self.objects:
            raise KeyError(f"missing object {oid}")
        return self.objects[oid]
