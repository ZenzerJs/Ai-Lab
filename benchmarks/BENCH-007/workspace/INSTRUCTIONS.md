# BENCH-007: Cache Invalidation & Billing Precision Regression

## Assignment
Fix the interdependent state, cache-invalidation, defensive-copy, and monetary-rounding bugs across four modules:
- `store.py` (`TenantStore`)
- `cache.py` (`InvoiceCache`)
- `billing.py` (`calculate_invoice`)
- `api.py` (`BillingAPI`)

## Public API & Invariants

### 1. `store.py` (`TenantStore`)
Supported tiers in `TIER_CATALOG`:
- `"starter"`: `unit_rate = "0.10"`, `discount_rate = "0.00"`
- `"pro"`: `unit_rate = "0.08"`, `discount_rate = "0.10"`
- `"enterprise"`: `unit_rate = "0.05"`, `discount_rate = "0.20"`

Methods on `TenantStore`:
- `upsert_tenant(tenant_id: str, tier: str = "starter") -> dict`:
  Creates or updates a tenant. New tenants start at `version = 1`; updating an existing tenant increments `version` by 1 and triggers invalidation hooks. Raises `ValueError` for unknown tiers.
- `update_tenant_tier(tenant_id: str, new_tier: str) -> dict`:
  Updates the tenant's `tier`, `unit_rate`, and `discount_rate`, increments `version` by 1, and invokes registered invalidation hooks `(tenant_id, None)`. Raises `KeyError` for unknown `tenant_id` and `ValueError` for unknown `new_tier`.
- `register_invalidation_hook(callback: Callable[[str, Optional[str]], None]) -> None`:
  Registers a callback invoked on tier or usage mutations.
- `record_usage(tenant_id: str, period: str, sku: str, units: Any, unit_rate: Optional[Any] = None) -> dict`:
  Records a usage line for `(tenant_id, period)`. Validates `units >= 0` and (when provided) `unit_rate >= 0`. Increments the tenant's `version` by 1 and invokes registered invalidation hooks `(tenant_id, period)`.
- `get_tenant(tenant_id: str) -> dict` and `get_snapshot(tenant_id: str, period: str) -> dict`:
  Return defensive deep copies so caller mutations cannot corrupt internal store state. `get_snapshot` returns:
  `{"tenant_id": str, "period": str, "tier": str, "unit_rate": Decimal, "discount_rate": Decimal, "version": int, "lines": list[dict]}`.

### 2. `cache.py` (`InvoiceCache`)
Methods on `InvoiceCache`:
- `get(tenant_id: str, period: str, version: Optional[int] = None) -> Optional[dict]`:
  Returns a deep copy of the cached invoice for `(tenant_id, period)`. When `version` is provided, returns `None` if the cached entry's version does not match `version`.
- `set(tenant_id: str, period: str, invoice: dict, version: Optional[int] = None) -> None`:
  Stores a deep copy of `invoice` associated with `(tenant_id, period)` and `resolved_version = version if version is not None else invoice.get("version", 1)`. Mutating the dict before or after `set` or `get` must never mutate cached entries.
- `invalidate(tenant_id: str, period: Optional[str] = None) -> int`:
  If `period` is specified, removes `(tenant_id, period)` and returns `1` if removed (`0` otherwise). If `period` is `None`, removes all cached periods for `tenant_id` and returns the count removed.
- `clear() -> None`: Clears all cached entries.

### 3. `billing.py` (`calculate_invoice`)
Function: `calculate_invoice(snapshot: dict, cached_invoice: Optional[dict] = None) -> dict`
- All monetary arithmetic MUST use `decimal.Decimal` (converting non-`Decimal` inputs via `Decimal(str(value))`) and quantize to `Decimal("0.01")` using `ROUND_HALF_UP`. Never use binary float arithmetic.
- If `cached_invoice` is provided and matches `(tenant_id, period, version)` of `snapshot`, return a defensive deep copy of `cached_invoice` without re-applying discounts. If `cached_invoice` is `None` or stale (version/tenant/period mismatch), recompute authoritatively from `snapshot`.
- Calculation order:
  1. For each line: `line_rate = line["unit_rate"]` if not `None` else `snapshot["unit_rate"]`; `line_total = quantize_money(Decimal(units) * Decimal(line_rate))`.
  2. `subtotal = quantize_money(sum(line_totals))`.
  3. `discount_amount = quantize_money(subtotal * Decimal(discount_rate))`.
  4. `total = quantize_money(subtotal - discount_amount)`.
- Return dictionary keys: `tenant_id`, `period`, `tier`, `version`, `lines`, `subtotal`, `discount_rate`, `discount_amount`, `total` (where `unit_rate`, `line_total`, `subtotal`, `discount_rate`, `discount_amount`, and `total` are `Decimal` instances).

### 4. `api.py` (`BillingAPI`)
- `BillingAPI(store: Optional[TenantStore] = None, cache: Optional[InvoiceCache] = None)`
- Wires store invalidation hooks to `cache.invalidate`.
- `create_tenant(tenant_id: str, tier: str = "starter") -> dict`
- `record_usage(tenant_id: str, period: str, sku: str, units: Any, unit_rate: Optional[Any] = None) -> dict`:
  Records usage and ensures cached entries for `(tenant_id, period)` are invalidated.
- `preview_invoice(tenant_id: str, period: str) -> dict`:
  Acquires an atomic versioned snapshot from `store`, checks `cache.get(tenant_id, period, version=snapshot["version"])`, calculates via `calculate_invoice(snapshot)` on miss, caches with `version=snapshot["version"]`, and returns a defensive deep copy.
- `change_tier_and_preview(tenant_id: str, new_tier: str, period: str) -> dict`:
  Updates tenant tier, invalidates all cached periods for `tenant_id`, and returns a fresh `preview_invoice(tenant_id, period)`.
