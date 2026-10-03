"""
models.py - Shared data models and exceptions for BENCH-002.
"""
from dataclasses import dataclass
from typing import List


class ApiError(Exception):
    """Raised when an API request fails or returns an error response."""
    pass


@dataclass
class Item:
    id: int
    name: str
    category: str


@dataclass
class PaginationMeta:
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


@dataclass
class PaginatedResult:
    items: List[Item]
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool
