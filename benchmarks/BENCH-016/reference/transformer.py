"""Schema validation and deterministic type coercion."""
import math
import re

_INT_RE = re.compile(r"-?\d+")
_KINDS = ("int", "float", "str")


def coerce(value, kind):
    if kind == "int":
        if isinstance(value, bool):
            raise ValueError("bool is not an int")
        if isinstance(value, int):
            return value
        if isinstance(value, str) and _INT_RE.fullmatch(value.strip()):
            return int(value.strip())
        raise ValueError("not coercible to int")
    if kind == "float":
        if isinstance(value, bool):
            raise ValueError("bool is not a float")
        if isinstance(value, (int, float)):
            result = float(value)
        elif isinstance(value, str):
            result = float(value.strip())
        else:
            raise ValueError("not coercible to float")
        if not math.isfinite(result):
            raise ValueError("non-finite float")
        return result
    if kind == "str":
        if not isinstance(value, str):
            raise ValueError("not a string")
        return value
    raise ValueError(f"unknown kind: {kind}")


class Transformer:
    def __init__(self, schema):
        self.schema = dict(schema)
        for name, kind in self.schema.items():
            if not isinstance(name, str) or not name:
                raise ValueError("field names must be nonempty strings")
            if kind not in _KINDS:
                raise ValueError(f"unknown kind: {kind}")

    def transform(self, data):
        if not isinstance(data, dict):
            return None, "not_mapping"
        clean = {}
        for name, kind in self.schema.items():
            if name not in data or data[name] is None:
                return None, f"missing_field:{name}"
            try:
                clean[name] = coerce(data[name], kind)
            except (ValueError, TypeError):
                return None, f"bad_type:{name}"
        return clean, None
