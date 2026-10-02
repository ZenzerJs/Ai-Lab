"""
api_server.py - Deliberately flawed solution for BENCH-002.
Server-only fix: updates server without coordinating with api_client.py.
"""
import math
from typing import Any, Dict, List, Optional

DATABASE_ITEMS = [
    {"id": i, "name": f"Item {i}", "category": "electronics" if i % 2 == 0 else "supplies"}
    for i in range(1, 26)
]


def handle_get_items(params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = params or {}
    page = int(params.get("page", 1))
    page_size = int(params.get("page_size", 10))

    if page < 1 or page_size < 1:
        return {
            "status": 400,
            "error": {"code": "INVALID_PAGINATION", "message": "page and page_size must be >= 1"},
        }

    total_items = len(DATABASE_ITEMS)
    total_pages = max(1, math.ceil(total_items / page_size))
    start_idx = (page - 1) * page_size
    items = DATABASE_ITEMS[start_idx:start_idx + page_size]

    return {
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
    }


def handle_health_check() -> Dict[str, Any]:
    return {"status": "healthy", "version": "1.2.0"}
