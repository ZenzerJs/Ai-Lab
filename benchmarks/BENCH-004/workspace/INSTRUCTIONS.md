# BENCH-004: Frontend Filter Table Stateful Regression

## Assignment
Fix state synchronization bugs in `filter_table.py`. The filter controller has regressions where matching item counts become stale, clearing filters fails to restore the full dataset, keyboard reset (`Escape`) is ignored, and rapid async sequence updates introduce race conditions.

## Component Contract: `TableFilterController`

Constructor: `TableFilterController(data: list[dict] = None)`
- Default data: loads 50 records from `sample_data.json` if data is None.

Methods:
1. `set_search(query: str)`:
   - Filters rows where `name` or `description` contains `query` (case-insensitive).
   - Recomputes both `displayed_rows` and `matching_count`.
2. `set_category(category: Optional[str])`:
   - Filters rows by `category`. Passing `None` or `""` selects all categories.
   - Recomputes `matching_count`.
3. `clear_filters()`:
   - Resets search query to `""` and category to `None`.
   - Restores all rows and resets `matching_count` to full count.
   - Resets empty state.
4. `handle_key_event(key: str)`:
   - `"Escape"`: Clears all filters immediately.
   - `"Enter"`: Commits current filter.
5. `apply_async_query(query: str, sequence_id: int)`:
   - Applies an asynchronous search query.
   - If `sequence_id < self._latest_sequence_id`, it is a stale out-of-order response and MUST BE IGNORED.
6. `get_view_state() -> dict`:
   - Returns:
     ```python
     {
         "displayed_rows": list[dict],
         "matching_count": int,
         "total_count": int,
         "active_filters": {"query": str, "category": Optional[str]},
         "is_empty": bool,
         "empty_message": Optional[str],
     }
     ```
   - When `matching_count == 0`: `is_empty` is `True`, `empty_message` is `"No records match the active filters"`.
   - When `matching_count > 0`: `is_empty` is `False`, `empty_message` is `None`.
