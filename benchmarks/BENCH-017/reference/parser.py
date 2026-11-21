"""Five-field cron expression parser."""
from models import FIELDS, CronSchedule


def _atom(token, spec):
    value = spec.names.get(token.upper())
    if value is None:
        if not token.isdigit():
            raise ValueError(f"invalid {spec.name} token: {token!r}")
        value = int(token)
    if value < spec.minimum or value > spec.maximum:
        raise ValueError(f"{spec.name} value out of range: {token!r}")
    return value


def _bounds(token, spec):
    if token == "*":
        return spec.minimum, spec.maximum
    if "-" in token:
        low_token, _, high_token = token.partition("-")
        low, high = _atom(low_token, spec), _atom(high_token, spec)
        if low > high:
            raise ValueError(f"reversed {spec.name} range: {token!r}")
        return low, high
    return _atom(token, spec), spec.maximum


def parse_field(expr, spec):
    """Parse one cron field into a frozenset of integers."""
    if not isinstance(expr, str) or not expr.strip():
        raise ValueError("empty cron field")
    values = set()
    for part in expr.split(","):
        part = part.strip()
        if not part:
            raise ValueError("empty list element")
        if part.count("/") > 1:
            raise ValueError(f"too many '/' in {part!r}")
        if "/" in part:
            range_part, _, step_part = part.partition("/")
            if not step_part.isdigit() or int(step_part) <= 0:
                raise ValueError(f"invalid step: {part!r}")
            low, high = _bounds(range_part, spec)
            values.update(range(low, high + 1, int(step_part)))
        elif part == "*":
            values.update(range(spec.minimum, spec.maximum + 1))
        elif "-" in part:
            low, high = _bounds(part, spec)
            values.update(range(low, high + 1))
        else:
            values.add(_atom(part, spec))
    if spec.name == "weekday":
        values = {0 if v == 7 else v for v in values}
    return frozenset(values)


def parse(expr):
    """Parse a 5-field cron expression into a CronSchedule."""
    if not isinstance(expr, str):
        raise ValueError("cron expression must be a string")
    parts = expr.split()
    if len(parts) != len(FIELDS):
        raise ValueError(f"expected {len(FIELDS)} fields, got {len(parts)}")
    values = [parse_field(part, spec) for part, spec in zip(parts, FIELDS)]
    return CronSchedule(*values, raw=expr)
