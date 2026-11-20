"""
api.py - Public billing API facade for BENCH-007.
"""
from typing import Any, Dict, Optional

from billing import calculate_invoice
from cache import InvoiceCache
from store import TenantStore


class BillingAPI:
    """
    BROKEN: Wires store, cache, and billing without cache invalidation hooks,
    versioned cache lookups, or defensive copies.
    """

    def __init__(
        self,
        store: Optional[TenantStore] = None,
        cache: Optional[InvoiceCache] = None,
    ) -> None:
        self.store = store if store is not None else TenantStore()
        self.cache = cache if cache is not None else InvoiceCache()

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
        """BROKEN: Records usage without invalidating stale cached invoice."""
        return self.store.record_usage(
            tenant_id, period, sku, units, unit_rate=unit_rate
        )

    def preview_invoice(self, tenant_id: str, period: str) -> Dict[str, Any]:
        """BROKEN: Ignores snapshot version during cache lookup/store and leaks refs."""
        snapshot = self.store.get_snapshot(tenant_id, period)
        cached = self.cache.get(tenant_id, period)
        if cached is not None:
            return cached
        invoice = calculate_invoice(snapshot)
        self.cache.set(tenant_id, period, invoice)
        return invoice

    def change_tier_and_preview(
        self, tenant_id: str, new_tier: str, period: str
    ) -> Dict[str, Any]:
        """BROKEN: Does not invalidate cache after updating tenant tier."""
        self.store.update_tenant_tier(tenant_id, new_tier)
        return self.preview_invoice(tenant_id, period)
