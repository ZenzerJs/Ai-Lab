# BENCH-002: Cross-File API Contract

## Assignment
Update the server endpoint in `api_server.py` and the client adapter in `api_client.py` from the legacy flat list response to the new documented paginated response contract.

## API Specification

### Server Endpoint (`api_server.py`)
Function: `handle_get_items(params: dict = None) -> dict`
- Input params:
  - `page`: positive integer (default 1)
  - `page_size`: positive integer (default 10)
- Response format:
```json
{
  "items": [
    {"id": 1, "name": "Item 1", "category": "tools"},
    ...
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total_items": 25,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false
  }
}
```
- Invalid parameters: If `page < 1` or `page_size < 1`:
  Return `{"status": 400, "error": {"code": "INVALID_PAGINATION", "message": "page and page_size must be >= 1"}}`.
- Beyond total pages: If `page > total_pages`, return empty list for `items` with valid `pagination` metadata (NOT an error response).
- Preserve existing endpoints: `handle_health_check()` must remain unchanged and functional.

### Client Adapter (`api_client.py`)
Class: `ApiClient`
Method: `fetch_items_page(page: int = 1, page_size: int = 10) -> PaginatedResult`
- Returns a `PaginatedResult` object with attributes:
  - `items`: list of `Item` dataclass instances
  - `page`: int
  - `page_size`: int
  - `total_items`: int
  - `total_pages`: int
  - `has_next`: bool
  - `has_prev`: bool
- Error responses: If the server returns an error (status >= 400 or error dictionary), raise `ApiError` with the server error message. Never masquerade an error as an empty item list!
- Empty pages: When the server returns 0 items for an out-of-range page, return a valid `PaginatedResult` with `items=[]` and the corresponding pagination metadata.

## Models (`models.py`)
- Dataclasses: `Item`, `PaginationMeta`, `PaginatedResult`
- Exception: `ApiError`
