"""
api_server.py - Reference solution for BENCH-002.
"""
import math
from typing import Any, Dict, List, Optional

DATABASE_ITEMS = [
    {"id": i, "name": f"Item {i}", "category": "electronics" if i % 2 == 0 else "supplies"}
    for i in range(1, 26)
]


def handle_get_items(params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Paginated items endpoint adhering to the contract."""
    params = params or {}
    page = params.get("page", 1)
    page_size = params.get("page_size", 10)

    try:
        page = int(page)
        page_size = int(page_size)
    except (ValueError, TypeError):
        return {
            "status": 400,
            "error": {"code": "INVALID_PAGINATION", "message": "page and page_size must be integers"},
        }

    if page < 1 or page_size < 1:
        return {
            "status": 400,
            "error": {"code": "INVALID_PAGINATION", "message": "page and page_size must be >= 1"},
        }

    total_items = len(DATABASE_ITEMS)
    total_pages = max(1, math.ceil(total_items / page_size))

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size

    if start_idx >= total_items:
        items = []
    else:
        items = list(DATABASE_ITEMS[start_idx:end_idx])

    has_next = page < total_pages
    has_prev = page > 1

    return {
        "items": items,
        "pagination": {
          "page": page,
          "page_size": page_size,
          "total_items": total_items,
          "total_pages": total_pages,
          "has_next": has_next,
          "has_prev": has_prev,
        },
    }


def handle_health_check() -> Dict[str, Any]:
    """Unrelated endpoint preserved."""
    return {"status": "healthy", "version": "1.2.0"}
