"""
filter_table.py - Table filter controller implementation for BENCH-004.
BROKEN STATE: Contains state synchronization bugs, stale count cache,
missing Escape reset handler, and out-of-order sequence race conditions.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class TableFilterController:
    """Stateful controller for table search, category filter, and keyboard reset."""

    def __init__(self, data: Optional[List[Dict[str, Any]]] = None):
        if data is None:
            data_file = Path(__file__).resolve().parent / "sample_data.json"
            if data_file.exists():
                self.all_records = json.loads(data_file.read_text(encoding="utf-8"))
            else:
                self.all_records = []
        else:
            self.all_records = list(data)

        self._query: str = ""
        self._category: Optional[str] = None
        self._displayed_rows: List[Dict[str, Any]] = list(self.all_records)
        # Bug 1: Stale count cache that fails to synchronize on filter changes
        self._cached_matching_count: int = len(self.all_records)
        self._latest_sequence_id: int = 0

    def set_search(self, query: str) -> None:
        self._query = query.strip()
        self._recompute_rows()
        # Bug 1: Fails to update self._cached_matching_count here!

    def set_category(self, category: Optional[str]) -> None:
        self._category = category.strip() if category else None
        self._recompute_rows()
        # Bug 1: Fails to update self._cached_matching_count here!

    def _recompute_rows(self) -> None:
        rows = list(self.all_records)
        if self._category:
            rows = [r for r in rows if r.get("category") == self._category]
        if self._query:
            q_lower = self._query.lower()
            rows = [
                r for r in rows
                if q_lower in r.get("name", "").lower() or q_lower in r.get("description", "").lower()
            ]
        self._displayed_rows = rows

    def clear_filters(self) -> None:
        # Bug 2: Only clears query, forgets category and fails to restore count!
        self._query = ""
        self._recompute_rows()

    def handle_key_event(self, key: str) -> None:
        # Bug 3: Escape key does nothing!
        if key == "Enter":
            self._recompute_rows()

    def apply_async_query(self, query: str, sequence_id: int) -> None:
        # Bug 4: Does not verify sequence_id >= _latest_sequence_id, allowing stale overwrites!
        self._query = query
        self._recompute_rows()

    def get_view_state(self) -> Dict[str, Any]:
        count = self._cached_matching_count
        is_empty = (len(self._displayed_rows) == 0)
        return {
            "displayed_rows": list(self._displayed_rows),
            "matching_count": count,
            "total_count": len(self.all_records),
            "active_filters": {"query": self._query, "category": self._category},
            "is_empty": is_empty,
            "empty_message": "No records match the active filters" if is_empty else None,
        }
