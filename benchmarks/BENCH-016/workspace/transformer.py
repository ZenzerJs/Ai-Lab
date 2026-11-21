"""Schema validation and type coercion."""
import re

_INT_RE = re.compile(r"-?\d+")
_KINDS = ("int", "float", "str")


def coerce(value, kind):
    if kind == "int":
        if isinstance(value, int):
            return value
        if isinstance(value, str) and _INT_RE.fullmatch(value.strip()):
            return int(value.strip())
        raise ValueError("not coercible to int")
    if kind == "float":
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            return float(value.strip())
        raise ValueError("not coercible to float")
    if kind == "str":
        if not isinstance(value, str):
            raise ValueError("not a string")
        return value
    raise ValueError(f"unknown kind: {kind}")


class Transformer:
    def __init__(self, schema):
        self.schema = dict(schema)
        for name, kind in self.schema.items():
            if kind not in _KINDS:
                raise ValueError(f"unknown kind: {kind}")

    def transform(self, data):
        clean = {}
        for name, kind in self.schema.items():
            clean[name] = coerce(data[name], kind)
        return clean, None
