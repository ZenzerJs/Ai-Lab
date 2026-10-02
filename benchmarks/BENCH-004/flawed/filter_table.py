"""
filter_table.py - Deliberately flawed solution for BENCH-004.
Updates displayed rows but fails to update matching_count, leaving count stale.
"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class TableFilterController:
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
        # Flawed: static count that is never updated on search!
        self._matching_count: int = len(self.all_records)
        self._latest_sequence_id: int = 0

    def set_search(self, query: str) -> None:
        self._query = query.strip()
        self._recompute_rows()
        # Flawed: matching_count is not synchronized!

    def set_category(self, category: Optional[str]) -> None:
        self._category = category.strip() if category else None
        self._recompute_rows()

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
        self._query = ""
        self._category = None
        self._recompute_rows()

    def handle_key_event(self, key: str) -> None:
        # Flawed: Escape is ignored!
        pass

    def apply_async_query(self, query: str, sequence_id: int) -> None:
        self._query = query.strip()
        self._recompute_rows()

    def get_view_state(self) -> Dict[str, Any]:
        is_empty = (len(self._displayed_rows) == 0)
        return {
            "displayed_rows": list(self._displayed_rows),
            "matching_count": self._matching_count,
            "total_count": len(self.all_records),
            "active_filters": {"query": self._query, "category": self._category},
            "is_empty": is_empty,
            "empty_message": "No records match the active filters" if is_empty else None,
        }
