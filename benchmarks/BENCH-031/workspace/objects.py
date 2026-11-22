"""Content-addressed objects."""
import hashlib
import json


def object_id(kind, payload):
    body = json.dumps(payload)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


class ObjectStore:
    def __init__(self):
        self.objects = {}

    def put(self, kind, payload):
        oid = object_id(kind, payload)
        self.objects[oid] = (kind, payload)
        return oid

    def get(self, oid):
        if oid not in self.objects:
            raise KeyError(f"missing object {oid}")
        return self.objects[oid]
