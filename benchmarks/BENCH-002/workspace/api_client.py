"""
api_client.py - Client adapter for BENCH-002.
"""
from typing import Any, Dict, List, Optional
import api_server
from models import ApiError, Item, PaginatedResult


class ApiClient:
    """
    Client adapter consuming the items API.
    """
    def __init__(self, server_module=None):
        self.server = server_module or api_server

    def fetch_items_page(self, page: int = 1, page_size: int = 10) -> PaginatedResult:
        """
        BROKEN: Assumes server returns a flat list of dicts.
        Fails to parse pagination metadata, total_items, or total_pages.
        """
        raw = self.server.handle_get_items({"page": page, "page_size": page_size})
        # Legacy parsing: expects raw to be a list
        if isinstance(raw, list):
            items = [Item(id=x["id"], name=x["name"], category=x["category"]) for x in raw]
            return PaginatedResult(
                items=items,
                page=page,
                page_size=page_size,
                total_items=len(items),
                total_pages=1,
                has_next=False,
                has_prev=False,
            )
        # If server returns dict, this crashes or returns invalid pagination
        raise ApiError("Unexpected response shape")
