"""
store.py - Flawed partial patch for BENCH-007 (fixes store.py while leaving cache.py/api.py stale).
"""
import copy
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Dict, List, Optional, Tuple


TIER_CATALOG: Dict[str, Dict[str, str]] = {
    "starter": {"unit_rate": "0.10", "discount_rate": "0.00"},
    "pro": {"unit_rate": "0.08", "discount_rate": "0.10"},
    "enterprise": {"unit_rate": "0.05", "discount_rate": "0.20"},
}


def _to_decimal(value: Any, field_name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} cannot be a boolean")
    if isinstance(value, Decimal):
        dec = value
    else:
        try:
            dec = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError(f"Invalid decimal value for {field_name}: {value!r}") from exc
    if not dec.is_finite():
        raise ValueError(f"{field_name} must be finite")
    return dec


class TenantStore:
    """In-memory store holding versioned tenant state and usage records."""

    def __init__(self) -> None:
        self._tenants: Dict[str, Dict[str, Any]] = {}
        self._usage: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        self._invalidation_hooks: List[Callable[[str, Optional[str]], None]] = []

    def register_invalidation_hook(
        self, callback: Callable[[str, Optional[str]], None]
    ) -> None:
        """Register a callback invoked on tenant tier or usage mutations."""
        if callback not in self._invalidation_hooks:
            self._invalidation_hooks.append(callback)

    def _notify_invalidation(self, tenant_id: str, period: Optional[str]) -> None:
        for callback in self._invalidation_hooks:
            callback(tenant_id, period)

    def upsert_tenant(self, tenant_id: str, tier: str = "starter") -> Dict[str, Any]:
        """Create a tenant at version 1 or update existing tenant and bump version."""
        if tier not in TIER_CATALOG:
            raise ValueError(f"Unknown tier: {tier}")
        spec = TIER_CATALOG[tier]
        existing = self._tenants.get(tenant_id)
        version = existing["version"] + 1 if existing is not None else 1
        record = {
            "tenant_id": tenant_id,
            "tier": tier,
            "unit_rate": Decimal(spec["unit_rate"]),
            "discount_rate": Decimal(spec["discount_rate"]),
            "version": version,
        }
        self._tenants[tenant_id] = record
        if existing is not None:
            self._notify_invalidation(tenant_id, None)
        return copy.deepcopy(record)

    def update_tenant_tier(self, tenant_id: str, new_tier: str) -> Dict[str, Any]:
        """Update tenant tier, bump version, and trigger cache invalidation."""
        if tenant_id not in self._tenants:
            raise KeyError(f"Unknown tenant: {tenant_id}")
        if new_tier not in TIER_CATALOG:
            raise ValueError(f"Unknown tier: {new_tier}")

        spec = TIER_CATALOG[new_tier]
        tenant = self._tenants[tenant_id]
        tenant["tier"] = new_tier
        tenant["unit_rate"] = Decimal(spec["unit_rate"])
        tenant["discount_rate"] = Decimal(spec["discount_rate"])
        tenant["version"] += 1
        self._notify_invalidation(tenant_id, None)
        return copy.deepcopy(tenant)

    def record_usage(
        self,
        tenant_id: str,
        period: str,
        sku: str,
        units: Any,
        unit_rate: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Record usage line, bump tenant version, and invalidate period cache."""
        if tenant_id not in self._tenants:
            raise KeyError(f"Unknown tenant: {tenant_id}")
        dec_units = _to_decimal(units, "units")
        if dec_units < Decimal("0"):
            raise ValueError("units must be non-negative")

        dec_rate: Optional[Decimal] = None
        if unit_rate is not None:
            dec_rate = _to_decimal(unit_rate, "unit_rate")
            if dec_rate < Decimal("0"):
                raise ValueError("unit_rate must be non-negative")

        line = {
            "sku": sku,
            "units": dec_units,
            "unit_rate": dec_rate,
        }
        self._usage.setdefault((tenant_id, period), []).append(line)
        self._tenants[tenant_id]["version"] += 1
        self._notify_invalidation(tenant_id, period)
        return copy.deepcopy(line)

    def get_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """Return a defensive copy of the tenant record."""
        if tenant_id not in self._tenants:
            raise KeyError(f"Unknown tenant: {tenant_id}")
        return copy.deepcopy(self._tenants[tenant_id])

    def get_snapshot(self, tenant_id: str, period: str) -> Dict[str, Any]:
        """Return an atomic, defensive snapshot of tenant rates, version, and usage."""
        if tenant_id not in self._tenants:
            raise KeyError(f"Unknown tenant: {tenant_id}")
        tenant = self._tenants[tenant_id]
        lines = self._usage.get((tenant_id, period), [])
        return copy.deepcopy({
            "tenant_id": tenant_id,
            "period": period,
            "tier": tenant["tier"],
            "unit_rate": tenant["unit_rate"],
            "discount_rate": tenant["discount_rate"],
            "version": tenant["version"],
            "lines": lines,
        })
