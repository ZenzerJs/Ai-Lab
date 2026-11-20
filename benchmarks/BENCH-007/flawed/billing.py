"""
billing.py - Flawed partial patch for BENCH-007 (fixes billing.py while leaving cache.py/api.py stale).
"""
import copy
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, List, Optional


MONEY_QUANT = Decimal("0.01")


def to_decimal(value: Any) -> Decimal:
    """Convert numeric or string values to exact Decimal without float binary drift."""
    if isinstance(value, bool):
        raise ValueError("Monetary values cannot be booleans")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError(f"Invalid numeric value: {value!r}") from exc


def quantize_money(value: Decimal) -> Decimal:
    """Quantize a Decimal monetary amount to two decimal places using ROUND_HALF_UP."""
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def calculate_invoice(
    snapshot: Dict[str, Any],
    cached_invoice: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Calculate invoice deterministically using Decimal ROUND_HALF_UP.
    """
    if cached_invoice is not None:
        if (
            cached_invoice.get("tenant_id") == snapshot.get("tenant_id")
            and cached_invoice.get("period") == snapshot.get("period")
            and cached_invoice.get("version") == snapshot.get("version")
        ):
            return copy.deepcopy(cached_invoice)

    default_rate = to_decimal(snapshot["unit_rate"])
    discount_rate = to_decimal(snapshot["discount_rate"])

    computed_lines: List[Dict[str, Any]] = []
    subtotal = Decimal("0.00")

    for line in snapshot.get("lines", []):
        units = to_decimal(line["units"])
        rate = (
            to_decimal(line["unit_rate"])
            if line.get("unit_rate") is not None
            else default_rate
        )
        line_total = quantize_money(units * rate)
        subtotal += line_total
        computed_lines.append({
            "sku": line["sku"],
            "units": units,
            "unit_rate": rate,
            "line_total": line_total,
        })

    subtotal = quantize_money(subtotal)
    discount_amount = quantize_money(subtotal * discount_rate)
    total = quantize_money(subtotal - discount_amount)

    return {
        "tenant_id": snapshot["tenant_id"],
        "period": snapshot["period"],
        "tier": snapshot["tier"],
        "version": int(snapshot["version"]),
        "lines": computed_lines,
        "subtotal": subtotal,
        "discount_rate": discount_rate,
        "discount_amount": discount_amount,
        "total": total,
    }
