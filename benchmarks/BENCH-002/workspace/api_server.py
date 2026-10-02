"""
api_server.py - Server handler for BENCH-002.
"""
from typing import Any, Dict, List, Optional

# Static mock database of 25 items
DATABASE_ITEMS = [
    {"id": i, "name": f"Item {i}", "category": "electronics" if i % 2 == 0 else "supplies"}
    for i in range(1, 26)
]


def handle_get_items(params: Optional[Dict[str, Any]] = None) -> Any:
    """
    BROKEN: Legacy implementation returns a flat unpaginated list of items.
    Does not support pagination query parameters or metadata.
    """
    # Legacy flat return:
    return list(DATABASE_ITEMS)


def handle_health_check() -> Dict[str, Any]:
    """Unrelated endpoint: must remain unchanged."""
    return {"status": "healthy", "version": "1.2.0"}
