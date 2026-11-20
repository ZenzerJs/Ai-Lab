"""
api.py - Reference BillingAPI wiring versioned snapshots and cache invalidation for BENCH-007.
"""
import copy
from typing import Any, Dict, Optional

from billing import calculate_invoice
from cache import InvoiceCache
from store import TenantStore


class BillingAPI:
    """Coordinated billing facade ensuring atomic versioned reads and cache invalidation."""

    def __init__(
        self,
        store: Optional[TenantStore] = None,
        cache: Optional[InvoiceCache] = None,
    ) -> None:
        self.store = store if store is not None else TenantStore()
        self.cache = cache if cache is not None else InvoiceCache()
        self.store.register_invalidation_hook(self.cache.invalidate)

    def create_tenant(self, tenant_id: str, tier: str = "starter") -> Dict[str, Any]:
        """Create or update a tenant."""
        return self.store.upsert_tenant(tenant_id, tier=tier)

    def record_usage(
        self,
        tenant_id: str,
        period: str,
        sku: str,
        units: Any,
        unit_rate: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Record usage and invalidate cached entry for the period."""
        line = self.store.record_usage(
            tenant_id, period, sku, units, unit_rate=unit_rate
        )
        self.cache.invalidate(tenant_id, period)
        return line

    def preview_invoice(self, tenant_id: str, period: str) -> Dict[str, Any]:
        """
        Return a defensive copy of the invoice for (tenant_id, period)
        matching the tenant's current snapshot version.
        """
        snapshot = self.store.get_snapshot(tenant_id, period)
        version = int(snapshot["version"])
        cached = self.cache.get(tenant_id, period, version=version)
        if cached is not None:
            return copy.deepcopy(cached)

        invoice = calculate_invoice(snapshot)
        self.cache.set(tenant_id, period, invoice, version=version)
        return copy.deepcopy(invoice)

    def change_tier_and_preview(
        self, tenant_id: str, new_tier: str, period: str
    ) -> Dict[str, Any]:
        """Update tenant tier, invalidate all cached periods, and preview updated invoice."""
        self.store.update_tenant_tier(tenant_id, new_tier)
        self.cache.invalidate(tenant_id)
        return self.preview_invoice(tenant_id, period)
