"""Five-field cron expression parser."""
from models import FIELDS, CronSchedule


def _atom(token, spec):
    value = spec.names.get(token)
    if value is None:
        if not token.isdigit():
            raise ValueError(f"invalid {spec.name} token: {token!r}")
        value = int(token)
    return value


def _bounds(token, spec):
    if token == "*":
        return spec.minimum, spec.maximum
    if "-" in token:
        low_token, _, high_token = token.partition("-")
        return _atom(low_token, spec), _atom(high_token, spec)
    return _atom(token, spec), spec.maximum


def parse_field(expr, spec):
    """Parse one cron field into a frozenset of integers."""
    if not isinstance(expr, str) or not expr.strip():
        raise ValueError("empty cron field")
    values = set()
    for part in expr.split(","):
        if "/" in part:
            range_part, _, step_part = part.partition("/")
            step = int(step_part)
            low, high = _bounds(range_part, spec)
            values.update(range(low, high + 1, step))
        elif part == "*":
            values.update(range(spec.minimum, spec.maximum + 1))
        elif "-" in part:
            low, high = _bounds(part, spec)
            values.update(range(low, high + 1))
        else:
            values.add(_atom(part, spec))
    return frozenset(values)


def parse(expr):
    """Parse a 5-field cron expression into a CronSchedule."""
    if not isinstance(expr, str):
        raise ValueError("cron expression must be a string")
    parts = expr.split(" ")
    if len(parts) != len(FIELDS):
        raise ValueError(f"expected {len(FIELDS)} fields, got {len(parts)}")
    values = [parse_field(part, spec) for part, spec in zip(parts, FIELDS)]
    return CronSchedule(*values)
