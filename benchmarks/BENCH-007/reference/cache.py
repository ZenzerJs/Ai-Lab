"""
cache.py - Reference versioned and isolated InvoiceCache for BENCH-007.
"""
import copy
from typing import Any, Dict, Optional, Tuple


class InvoiceCache:
    """Version-aware invoice cache with defensive copying and period/tenant invalidation."""

    def __init__(self) -> None:
        self._entries: Dict[Tuple[str, str], Tuple[int, Dict[str, Any]]] = {}

    def get(
        self,
        tenant_id: str,
        period: str,
        version: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Return a deep copy of the cached invoice if present and version matches.
        """
        entry = self._entries.get((tenant_id, period))
        if entry is None:
            return None
        entry_version, invoice = entry
        if version is not None and entry_version != int(version):
            return None
        return copy.deepcopy(invoice)

    def set(
        self,
        tenant_id: str,
        period: str,
        invoice: Dict[str, Any],
        version: Optional[int] = None,
    ) -> None:
        """Store a defensive copy of the invoice keyed by (tenant_id, period) and version."""
        resolved_version = (
            int(version) if version is not None else int(invoice.get("version", 1))
        )
        self._entries[(tenant_id, period)] = (resolved_version, copy.deepcopy(invoice))

    def invalidate(self, tenant_id: str, period: Optional[str] = None) -> int:
        """
        Invalidate cached entry for (tenant_id, period) or all periods for tenant_id
        when period is None.
        """
        if period is not None:
            removed = self._entries.pop((tenant_id, period), None)
            return 1 if removed is not None else 0

        matching_keys = [key for key in self._entries if key[0] == tenant_id]
        for key in matching_keys:
            self._entries.pop(key, None)
        return len(matching_keys)

    def clear(self) -> None:
        """Clear all entries from the cache."""
        self._entries.clear()
