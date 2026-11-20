"""
evaluator.py - Protected evaluator for BENCH-007.
Verifies Decimal ROUND_HALF_UP billing precision, no double-discounting,
cross-file cache invalidation on tier/usage changes, and defensive copying.
"""
from decimal import Decimal
import sys


def _fail(reason: str, detail: str) -> None:
    print(f"REASON: {reason}", file=sys.stderr)
    print(detail, file=sys.stderr)
    sys.exit(1)


def run_checks() -> None:
    try:
        from api import BillingAPI
        from billing import calculate_invoice
        from cache import InvoiceCache
        from store import TenantStore
    except Exception as exc:
        _fail("import_error", f"Failed to import BENCH-007 modules: {exc}")

    # Check 1: Decimal exact penny ties (0.1 + 0.2, 0.005, 0.015, 1.005 ROUND_HALF_UP)
    snap_ties = {
        "tenant_id": "t_dec",
        "period": "2026-11",
        "tier": "starter",
        "unit_rate": Decimal("0.10"),
        "discount_rate": Decimal("0.00"),
        "version": 1,
        "lines": [
            {"sku": "line_a", "units": 1, "unit_rate": "0.1"},
            {"sku": "line_b", "units": 1, "unit_rate": "0.2"},
        ],
    }
    inv_ties = calculate_invoice(snap_ties)
    if not isinstance(inv_ties.get("subtotal"), Decimal) or not isinstance(inv_ties.get("total"), Decimal):
        _fail(
            "stale_cache_or_billing_rounding_drift",
            f"Expected Decimal monetary fields, got subtotal={type(inv_ties.get('subtotal'))}, total={type(inv_ties.get('total'))}",
        )
    if inv_ties["subtotal"] != Decimal("0.30") or inv_ties["total"] != Decimal("0.30"):
        _fail(
            "stale_cache_or_billing_rounding_drift",
            f"0.1 + 0.2 drift: expected Decimal('0.30'), got subtotal={inv_ties['subtotal']!r}, total={inv_ties['total']!r}",
        )

    snap_half = {
        "tenant_id": "t_half",
        "period": "2026-11",
        "tier": "pro",
        "unit_rate": Decimal("0.08"),
        "discount_rate": Decimal("0.10"),
        "version": 1,
        "lines": [
            {"sku": "half_cent", "units": 1, "unit_rate": "0.005"},
            {"sku": "three_half", "units": 3, "unit_rate": "0.005"},
            {"sku": "one_oh_five", "units": 1, "unit_rate": "1.005"},
            {"sku": "tenth", "units": 1, "unit_rate": "0.1"},
            {"sku": "fifth", "units": 1, "unit_rate": "0.2"},
        ],
    }
    inv_half = calculate_invoice(snap_half)
    # Lines: 0.01 + 0.02 + 1.01 + 0.10 + 0.20 = 1.34; 10% discount = 0.134 -> 0.13; total = 1.21
    expected_lines = [
        Decimal("0.01"),
        Decimal("0.02"),
        Decimal("1.01"),
        Decimal("0.10"),
        Decimal("0.20"),
    ]
    actual_lines = [line["line_total"] for line in inv_half["lines"]]
    if actual_lines != expected_lines:
        _fail(
            "stale_cache_or_billing_rounding_drift",
            f"ROUND_HALF_UP multi-line mismatch: expected {expected_lines}, got {actual_lines}",
        )
    if (
        inv_half["subtotal"] != Decimal("1.34")
        or inv_half["discount_amount"] != Decimal("0.13")
        or inv_half["total"] != Decimal("1.21")
    ):
        _fail(
            "stale_cache_or_billing_rounding_drift",
            f"Multi-line invoice total drift: {inv_half}",
        )

    # Half-cent discount tie: 0.05 * 0.10 = 0.005 -> ROUND_HALF_UP = 0.01
    snap_disc_half = {
        "tenant_id": "t_dhalf",
        "period": "2026-11",
        "tier": "pro",
        "unit_rate": Decimal("0.08"),
        "discount_rate": Decimal("0.10"),
        "version": 1,
        "lines": [{"sku": "nickel", "units": 1, "unit_rate": "0.05"}],
    }
    inv_dhalf = calculate_invoice(snap_disc_half)
    if inv_dhalf["discount_amount"] != Decimal("0.01") or inv_dhalf["total"] != Decimal("0.04"):
        _fail(
            "stale_cache_or_billing_rounding_drift",
            f"Half-cent discount tie failed: expected discount=0.01, total=0.04, got {inv_dhalf}",
        )

    # Check 2: No double-applied discount when cached_invoice is passed
    inv_reused = calculate_invoice(snap_half, cached_invoice=inv_half)
    if inv_reused["total"] != Decimal("1.21") or inv_reused["discount_amount"] != Decimal("0.13"):
        _fail(
            "stale_cache_or_billing_rounding_drift",
            f"Double discount detected when cached_invoice supplied: {inv_reused}",
        )
    # Stale cached_invoice with older version must be ignored and recomputed from snapshot
    snap_half_v2 = dict(snap_half)
    snap_half_v2["version"] = 2
    snap_half_v2["discount_rate"] = Decimal("0.20")
    inv_recomputed = calculate_invoice(snap_half_v2, cached_invoice=inv_half)
    # 1.34 * 0.20 = 0.268 -> 0.27; total = 1.07
    if inv_recomputed["total"] != Decimal("1.07") or inv_recomputed["version"] != 2:
        _fail(
            "stale_cache_or_billing_rounding_drift",
            f"Stale cached_invoice with mismatched version was not recomputed: {inv_recomputed}",
        )

    # Check 3: Cross-file cache invalidation on tier change & usage additions
    store = TenantStore()
    cache = InvoiceCache()
    api = BillingAPI(store=store, cache=cache)
    api.create_tenant("t_corp", tier="starter")
    api.record_usage("t_corp", "2026-11", "compute", 100)
    api.record_usage("t_corp", "2026-12", "compute", 50)

    p_nov_v1 = api.preview_invoice("t_corp", "2026-11")
    p_dec_v1 = api.preview_invoice("t_corp", "2026-12")
    if p_nov_v1["total"] != Decimal("10.00") or p_dec_v1["total"] != Decimal("5.00"):
        _fail(
            "stale_cache_or_billing_rounding_drift",
            f"Initial starter previews incorrect: nov={p_nov_v1['total']}, dec={p_dec_v1['total']}",
        )

    # Repeated preview must not double-discount or mutate
    p_nov_repeat = api.preview_invoice("t_corp", "2026-11")
    if p_nov_repeat["total"] != Decimal("10.00"):
        _fail(
            "stale_cache_or_billing_rounding_drift",
            f"Repeated preview altered total: {p_nov_repeat['total']}",
        )

    # Tier change invalidates ALL cached periods for tenant
    p_nov_ent = api.change_tier_and_preview("t_corp", "enterprise", "2026-11")
    if (
        p_nov_ent["tier"] != "enterprise"
        or p_nov_ent["subtotal"] != Decimal("5.00")
        or p_nov_ent["discount_amount"] != Decimal("1.00")
        or p_nov_ent["total"] != Decimal("4.00")
        or p_nov_ent["version"] <= p_nov_v1["version"]
    ):
        _fail(
            "stale_cache_or_billing_rounding_drift",
            f"Tier change returned stale or wrong invoice: {p_nov_ent}",
        )

    p_dec_ent = api.preview_invoice("t_corp", "2026-12")
    if p_dec_ent["tier"] != "enterprise" or p_dec_ent["total"] != Decimal("2.00"):
        _fail(
            "stale_cache_or_billing_rounding_drift",
            f"Second period 2026-12 remained stale after tier change: {p_dec_ent}",
        )

    # Recording usage after preview invalidates period cache
    api.record_usage("t_corp", "2026-11", "burst", 20, unit_rate="0.10")
    p_nov_burst = api.preview_invoice("t_corp", "2026-11")
    # 100*0.05 + 20*0.10 = 7.00; 20% discount = 1.40; total = 5.60
    if p_nov_burst["subtotal"] != Decimal("7.00") or p_nov_burst["total"] != Decimal("5.60"):
        _fail(
            "stale_cache_or_billing_rounding_drift",
            f"Usage addition did not invalidate cached period: {p_nov_burst}",
        )

    # Direct store tier update also busts stale cache via hook / version check
    store.update_tenant_tier("t_corp", "pro")
    p_nov_pro = api.preview_invoice("t_corp", "2026-11")
    # 100*0.08 + 20*0.10 = 10.00; 10% discount = 1.00; total = 9.00
    if p_nov_pro["tier"] != "pro" or p_nov_pro["total"] != Decimal("9.00"):
        _fail(
            "stale_cache_or_billing_rounding_drift",
            f"Direct store tier mutation left stale cache: {p_nov_pro}",
        )

    # Check 4: Cache and store isolation against caller mutation
    mutated = api.preview_invoice("t_corp", "2026-11")
    mutated["total"] = Decimal("9999.99")
    mutated["lines"][0]["units"] = Decimal("999999")
    mutated["lines"].append({"sku": "injected", "units": 1, "unit_rate": Decimal("1.00"), "line_total": Decimal("1.00")})

    fresh = api.preview_invoice("t_corp", "2026-11")
    if fresh["total"] != Decimal("9.00") or len(fresh["lines"]) != 2 or fresh["lines"][0]["units"] != Decimal("100"):
        _fail(
            "stale_cache_or_billing_rounding_drift",
            f"Cache leaked mutable reference to caller: {fresh}",
        )

    # Direct cache set/get isolation and version gating
    payload = {"tenant_id": "iso", "period": "2026-01", "version": 3, "total": Decimal("12.34"), "lines": [{"sku": "a"}]}
    cache.set("iso", "2026-01", payload, version=3)
    payload["total"] = Decimal("0.00")
    payload["lines"].append({"sku": "b"})

    got_v3 = cache.get("iso", "2026-01", version=3)
    got_v4 = cache.get("iso", "2026-01", version=4)
    if got_v3 is None or got_v3["total"] != Decimal("12.34") or len(got_v3["lines"]) != 1:
        _fail(
            "stale_cache_or_billing_rounding_drift",
            f"InvoiceCache.set failed defensive copy isolation: {got_v3}",
        )
    if got_v4 is not None:
        _fail(
            "stale_cache_or_billing_rounding_drift",
            f"InvoiceCache.get ignored version mismatch (requested v4, got {got_v4})",
        )

    snap_copy = store.get_snapshot("t_corp", "2026-11")
    snap_copy["lines"].clear()
    if len(store.get_snapshot("t_corp", "2026-11")["lines"]) != 2:
        _fail(
            "stale_cache_or_billing_rounding_drift",
            "TenantStore.get_snapshot leaked mutable lines reference",
        )

    print("ALL CHECKS PASSED")
    sys.exit(0)


if __name__ == "__main__":
    run_checks()
