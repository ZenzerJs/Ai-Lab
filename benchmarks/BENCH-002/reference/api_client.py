"""
api_client.py - Reference solution for BENCH-002.
"""
from typing import Any, Dict, List, Optional
import api_server
from models import ApiError, Item, PaginatedResult


class ApiClient:
    """Client adapter updated to consume paginated responses."""
    def __init__(self, server_module=None):
        self.server = server_module or api_server

    def fetch_items_page(self, page: int = 1, page_size: int = 10) -> PaginatedResult:
        res = self.server.handle_get_items({"page": page, "page_size": page_size})

        if isinstance(res, dict) and (res.get("status", 200) >= 400 or "error" in res):
            err_info = res.get("error", {})
            err_msg = err_info.get("message", "API request failed") if isinstance(err_info, dict) else str(err_info)
            raise ApiError(f"API error: {err_msg}")

        if not isinstance(res, dict) or "items" not in res or "pagination" not in res:
            raise ApiError("Invalid response structure from server")

        pag = res["pagination"]
        items = [Item(id=x["id"], name=x["name"], category=x["category"]) for x in res["items"]]

        return PaginatedResult(
            items=items,
            page=pag["page"],
            page_size=pag["page_size"],
            total_items=pag["total_items"],
            total_pages=pag["total_pages"],
            has_next=pag["has_next"],
            has_prev=pag["has_prev"],
        )
