"""Rate-limiter models: decisions, quotas, rules, exceptions."""
from dataclasses import dataclass
from enum import Enum


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class ConfigError(ValueError):
    """Raised for unusable quota/bucket/rule configuration."""


@dataclass(frozen=True)
class Quota:
    """A named limit: `limit` events (or tokens) per `window_seconds`.

    kind: "fixed" (per window-start bucket), "sliding" (rolling log of
    event timestamps), or "bucket" (token bucket with refill_per_second).
    """

    name: str
    limit: int
    window_seconds: float
    kind: str = "fixed"
    refill_per_second: float = 0.0

    def __post_init__(self):
        if isinstance(self.limit, bool) or not isinstance(self.limit, int) \
                or self.limit < 1:
            raise ConfigError("limit must be a positive int")
        if isinstance(self.window_seconds, bool) or self.window_seconds <= 0:
            raise ConfigError("window_seconds must be positive")
        if self.kind not in ("fixed", "sliding", "bucket"):
            raise ConfigError(f"unknown quota kind {self.kind!r}")
        if self.kind == "bucket" and \
                (self.refill_per_second <= 0
                 or not isinstance(self.refill_per_second, (int, float))
                 or isinstance(self.refill_per_second, bool)):
            raise ConfigError("bucket quotas need refill_per_second > 0")


@dataclass(frozen=True)
class Rule:
    """A chain rule: subjects matching `pattern` get `action`.

    pattern "*" matches every subject; "prefix:*" matches the prefix.
    """

    pattern: str
    action: Decision

    def __post_init__(self):
        if not isinstance(self.pattern, str) or not self.pattern:
            raise ConfigError("pattern must be a nonempty string")
        if isinstance(self.action, str):
            try:
                object.__setattr__(self, "action", Decision(self.action))
            except ValueError:
                raise ConfigError(f"unknown action {self.action!r}")
        elif not isinstance(self.action, Decision):
            raise ConfigError("action must be a Decision")

    def matches(self, subject):
        if self.pattern == "*":
            return True
        if self.pattern.endswith(":*"):
            return subject.startswith(self.pattern[:-1])
        return self.pattern == subject
