"""
billing.py - Invoice calculation logic for BENCH-007.
"""
from typing import Any, Dict, List, Optional


def calculate_invoice(
    snapshot: Dict[str, Any],
    cached_invoice: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    BROKEN: Uses binary float arithmetic instead of Decimal ROUND_HALF_UP,
    and double-applies discount when cached_invoice is supplied.
    """
    discount_rate = float(snapshot["discount_rate"])

    if cached_invoice is not None:
        # BUG: treats already-discounted cached total as pre-discount subtotal
        prior_total = float(cached_invoice.get("total", 0.0))
        discount_amount = round(prior_total * discount_rate, 2)
        total = round(prior_total - discount_amount, 2)
        result = dict(cached_invoice)
        result["discount_amount"] = discount_amount
        result["total"] = total
        return result

    default_rate = float(snapshot["unit_rate"])
    computed_lines: List[Dict[str, Any]] = []
    line_totals: List[float] = []

    for line in snapshot.get("lines", []):
        units = float(line["units"])
        rate = float(line["unit_rate"]) if line.get("unit_rate") is not None else default_rate
        line_total = round(units * rate, 2)
        line_totals.append(line_total)
        computed_lines.append({
            "sku": line["sku"],
            "units": units,
            "unit_rate": rate,
            "line_total": line_total,
        })

    # BUG: binary float sum drifts (e.g. 0.1 + 0.2 == 0.30000000000000004)
    subtotal = sum(line_totals)
    discount_amount = round(subtotal * discount_rate, 2)
    total = round(subtotal - discount_amount, 2)

    return {
        "tenant_id": snapshot["tenant_id"],
        "period": snapshot["period"],
        "tier": snapshot["tier"],
        "version": snapshot["version"],
        "lines": computed_lines,
        "subtotal": subtotal,
        "discount_rate": discount_rate,
        "discount_amount": discount_amount,
        "total": total,
    }
