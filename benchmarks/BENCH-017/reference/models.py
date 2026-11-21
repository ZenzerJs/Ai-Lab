"""Cron field specifications and schedule model."""
from dataclasses import dataclass
from typing import Dict, FrozenSet


@dataclass(frozen=True)
class FieldSpec:
    name: str
    minimum: int
    maximum: int
    names: Dict[str, int]


MINUTE = FieldSpec("minute", 0, 59, {})
HOUR = FieldSpec("hour", 0, 23, {})
DAY = FieldSpec("day", 1, 31, {})
MONTH = FieldSpec("month", 1, 12, {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
})
WEEKDAY = FieldSpec("weekday", 0, 7, {
    "SUN": 0, "MON": 1, "TUE": 2, "WED": 3,
    "THU": 4, "FRI": 5, "SAT": 6,
})

FIELDS = (MINUTE, HOUR, DAY, MONTH, WEEKDAY)

ALL_DAYS = frozenset(range(DAY.minimum, DAY.maximum + 1))
ALL_WEEKDAYS = frozenset(range(0, 7))


@dataclass(frozen=True)
class CronSchedule:
    minute: FrozenSet[int]
    hour: FrozenSet[int]
    day: FrozenSet[int]
    month: FrozenSet[int]
    weekday: FrozenSet[int]
    raw: str
