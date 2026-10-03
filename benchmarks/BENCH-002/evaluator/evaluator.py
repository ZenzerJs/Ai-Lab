"""
evaluator.py - Protected evaluator for BENCH-002.
Verifies cross-file contract synchronization between api_server and api_client.
"""
import sys


def run_checks():
    try:
        import api_server
        from api_client import ApiClient
        from models import ApiError, Item, PaginatedResult
    except Exception as exc:
        print(f"REASON: import_error\nFailed to import modules: {exc}", file=sys.stderr)
        sys.exit(1)

    # Check 1: Server returns paginated response shape
    try:
        raw_res = api_server.handle_get_items({"page": 1, "page_size": 10})
    except Exception as exc:
        print(f"REASON: client_server_contract_mismatch\nServer raised error on valid request: {exc}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(raw_res, dict) or "items" not in raw_res or "pagination" not in raw_res:
        print("REASON: client_server_contract_mismatch", file=sys.stderr)
        print("Server did not return paginated shape with 'items' and 'pagination' dict.", file=sys.stderr)
        sys.exit(1)

    pag = raw_res["pagination"]
    required_pag_keys = {"page", "page_size", "total_items", "total_pages", "has_next", "has_prev"}
    if not required_pag_keys.issubset(pag.keys()):
        print("REASON: client_server_contract_mismatch", file=sys.stderr)
        print(f"Pagination missing required keys. Expected {required_pag_keys}, got {set(pag.keys())}", file=sys.stderr)
        sys.exit(1)

    if len(raw_res["items"]) != 10 or pag["total_items"] != 25 or pag["total_pages"] != 3:
        print("REASON: client_server_contract_mismatch", file=sys.stderr)
        print(f"Server pagination metadata calculation incorrect: {pag}", file=sys.stderr)
        sys.exit(1)

    # Check 2: Client parses paginated response into PaginatedResult
    client = ApiClient(api_server)
    try:
        res_p2 = client.fetch_items_page(page=2, page_size=10)
    except Exception as exc:
        print("REASON: client_server_contract_mismatch", file=sys.stderr)
        print(f"Client failed to parse page 2 paginated response: {exc}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(res_p2, PaginatedResult):
        print("REASON: client_server_contract_mismatch", file=sys.stderr)
        print(f"Client did not return PaginatedResult instance: {type(res_p2)}", file=sys.stderr)
        sys.exit(1)

    if len(res_p2.items) != 10 or res_p2.items[0].id != 11:
        print("REASON: client_server_contract_mismatch", file=sys.stderr)
        print(f"Client items slice incorrect for page 2. First item: {res_p2.items[0] if res_p2.items else 'empty'}", file=sys.stderr)
        sys.exit(1)

    if res_p2.page != 2 or res_p2.total_items != 25 or res_p2.total_pages != 3:
        print("REASON: client_server_contract_mismatch", file=sys.stderr)
        print(f"Client pagination metadata mismatch: page={res_p2.page}, total={res_p2.total_items}", file=sys.stderr)
        sys.exit(1)

    if not res_p2.has_next or not res_p2.has_prev:
        print("REASON: client_server_contract_mismatch", file=sys.stderr)
        print("Client navigation flags incorrect for middle page 2.", file=sys.stderr)
        sys.exit(1)

    # Check 3: Empty page out of range
    try:
        res_empty = client.fetch_items_page(page=5, page_size=10)
    except Exception as exc:
        print("REASON: empty_page_error", file=sys.stderr)
        print(f"Client crashed on out-of-range empty page: {exc}", file=sys.stderr)
        sys.exit(1)

    if res_empty.items != [] or res_empty.total_items != 25:
        print("REASON: empty_page_mismatch", file=sys.stderr)
        print(f"Expected empty items list for page 5, got {res_empty.items}", file=sys.stderr)
        sys.exit(1)

    # Check 4: Error handling on invalid parameters
    try:
        client.fetch_items_page(page=0, page_size=10)
        print("REASON: missing_error_handling", file=sys.stderr)
        print("Client did not raise ApiError on invalid page=0 parameter.", file=sys.stderr)
        sys.exit(1)
    except ApiError:
        pass
    except Exception as exc:
        print("REASON: missing_error_handling", file=sys.stderr)
        print(f"Client raised wrong error type on page=0: {type(exc)}: {exc}", file=sys.stderr)
        sys.exit(1)

    # Check 5: Unrelated health endpoint preserved
    health = api_server.handle_health_check()
    if health != {"status": "healthy", "version": "1.2.0"}:
        print("REASON: unrelated_endpoint_broken", file=sys.stderr)
        print(f"Health check endpoint was modified: {health}", file=sys.stderr)
        sys.exit(1)

    print("ALL CHECKS PASSED")
    sys.exit(0)


if __name__ == "__main__":
    run_checks()
