"""B+Tree models."""
from dataclasses import dataclass


class InvalidConfig(ValueError):
    pass


class DuplicateKey(ValueError):
    pass


class KeyNotFound(KeyError):
    pass


@dataclass(frozen=True)
class Entry:
    key: int
    value: str


@dataclass(frozen=True)
class Config:
    """order = maximum keys per node."""

    order: int = 3

    @property
    def max_keys(self):
        return self.order

    @property
    def min_keys(self):
        return self.order // 2
