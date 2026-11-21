"""B+Tree models: configuration, entries, and exceptions."""
from dataclasses import dataclass


class InvalidConfig(ValueError):
    """Raised when a B+Tree order is unusable."""


class DuplicateKey(ValueError):
    """Raised when inserting a key that already exists."""


class KeyNotFound(KeyError):
    """Raised when deleting or updating a missing key."""


@dataclass(frozen=True)
class Entry:
    key: int
    value: str


@dataclass(frozen=True)
class Config:
    """order = maximum keys per node; min_keys = floor(order / 2)."""

    order: int = 3

    def __post_init__(self):
        if isinstance(self.order, bool) or not isinstance(self.order, int) \
                or self.order < 2:
            raise InvalidConfig("order must be an int >= 2")

    @property
    def max_keys(self):
        return self.order

    @property
    def min_keys(self):
        return self.order // 2
