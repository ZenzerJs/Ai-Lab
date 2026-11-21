"""Pure chained migration of historical event payloads."""
from copy import deepcopy

from schema import Event


def upcast(event):
    result = deepcopy(event)
    if result.schema_version < 3:
        payload = result.payload
        if result.schema_version == 1:
            payload["delta"] = payload.pop("amount")
            result.schema_version = 2
        elif result.schema_version == 2:
            payload.setdefault("metadata", {})
            result.schema_version = 3
    delta = result.payload.get("delta")
    if type(delta) is not int or not isinstance(result.payload.get("metadata"), dict):
        raise ValueError("invalid increment payload")
    return Event(result.event_type, result.payload, result.schema_version, result.stream_version)
