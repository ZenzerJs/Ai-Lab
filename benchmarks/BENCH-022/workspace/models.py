"""Rate-limiter models."""
from dataclasses import dataclass
from enum import Enum


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Quota:
    name: str
    limit: int
    window_seconds: float
    kind: str = "fixed"
    refill_per_second: float = 0.0


@dataclass(frozen=True)
class Rule:
    pattern: str
    action: Decision

    def matches(self, subject):
        if self.pattern == "*":
            return True
        if self.pattern.endswith(":*"):
            return subject.startswith(self.pattern[:-1])
        return self.pattern == subject
