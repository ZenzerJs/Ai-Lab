"""
store.py - Tenant metadata and usage store for BENCH-007.
"""
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional, Tuple


TIER_CATALOG: Dict[str, Dict[str, str]] = {
    "starter": {"unit_rate": "0.10", "discount_rate": "0.00"},
    "pro": {"unit_rate": "0.08", "discount_rate": "0.10"},
    "enterprise": {"unit_rate": "0.05", "discount_rate": "0.20"},
}


class TenantStore:
    """In-memory store holding tenant tier configuration and usage lines."""

    def __init__(self) -> None:
        self._tenants: Dict[str, Dict[str, Any]] = {}
        self._usage: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        self._invalidation_hooks: List[Callable[[str, Optional[str]], None]] = []

    def register_invalidation_hook(
        self, callback: Callable[[str, Optional[str]], None]
    ) -> None:
        """Register an invalidation callback invoked on store updates."""
        self._invalidation_hooks.append(callback)

    def upsert_tenant(self, tenant_id: str, tier: str = "starter") -> Dict[str, Any]:
        """Create or update a tenant record."""
        if tier not in TIER_CATALOG:
            raise ValueError(f"Unknown tier: {tier}")
        spec = TIER_CATALOG[tier]
        existing = self._tenants.get(tenant_id)
        version = existing["version"] if existing else 1
        record = {
            "tenant_id": tenant_id,
            "tier": tier,
            "unit_rate": float(spec["unit_rate"]),
            "discount_rate": float(spec["discount_rate"]),
            "version": version,
        }
        self._tenants[tenant_id] = record
        return dict(record)

    def update_tenant_tier(self, tenant_id: str, new_tier: str) -> Dict[str, Any]:
        """
        BROKEN: Updates tenant tier and rates without bumping version
        or firing invalidation hooks.
        """
        if tenant_id not in self._tenants:
            raise KeyError(f"Unknown tenant: {tenant_id}")
        if new_tier not in TIER_CATALOG:
            raise ValueError(f"Unknown tier: {new_tier}")

        spec = TIER_CATALOG[new_tier]
        tenant = self._tenants[tenant_id]
        tenant["tier"] = new_tier
        tenant["unit_rate"] = float(spec["unit_rate"])
        tenant["discount_rate"] = float(spec["discount_rate"])
        # BUG: does not increment tenant["version"] or notify hooks
        return dict(tenant)

    def record_usage(
        self,
        tenant_id: str,
        period: str,
        sku: str,
        units: Any,
        unit_rate: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """BROKEN: Records usage without bumping version or notifying hooks."""
        if tenant_id not in self._tenants:
            raise KeyError(f"Unknown tenant: {tenant_id}")
        if float(units) < 0:
            raise ValueError("units must be non-negative")
        if unit_rate is not None and float(unit_rate) < 0:
            raise ValueError("unit_rate must be non-negative")

        line = {
            "sku": sku,
            "units": units,
            "unit_rate": unit_rate,
        }
        self._usage.setdefault((tenant_id, period), []).append(line)
        return dict(line)

    def get_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """Retrieve tenant record."""
        if tenant_id not in self._tenants:
            raise KeyError(f"Unknown tenant: {tenant_id}")
        return self._tenants[tenant_id]

    def get_snapshot(self, tenant_id: str, period: str) -> Dict[str, Any]:
        """BROKEN: Returns shallow snapshot leaking internal mutable line dicts."""
        if tenant_id not in self._tenants:
            raise KeyError(f"Unknown tenant: {tenant_id}")
        tenant = self._tenants[tenant_id]
        lines = self._usage.get((tenant_id, period), [])
        return {
            "tenant_id": tenant_id,
            "period": period,
            "tier": tenant["tier"],
            "unit_rate": tenant["unit_rate"],
            "discount_rate": tenant["discount_rate"],
            "version": tenant["version"],
            "lines": lines,
        }
