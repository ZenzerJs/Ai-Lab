"""Policy model definitions."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Role:
    name: str
    parents: tuple = ()

    def __post_init__(self):
        object.__setattr__(self, "parents", tuple(self.parents))


@dataclass(frozen=True)
class Rule:
    role: str
    action: str
    resource: str
    effect: str = "allow"

    def __post_init__(self):
        if self.effect not in ("allow", "deny"):
            raise ValueError("invalid effect")


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: str
