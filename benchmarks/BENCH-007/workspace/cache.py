"""
cache.py - Invoice cache for BENCH-007.
"""
from typing import Any, Dict, Optional, Tuple


class InvoiceCache:
    """
    BROKEN: Keys only by (tenant_id, period) ignoring version,
    fails to invalidate across periods when period=None,
    and leaks mutable dict references directly.
    """

    def __init__(self) -> None:
        self._entries: Dict[Tuple[str, Optional[str]], Dict[str, Any]] = {}

    def get(
        self,
        tenant_id: str,
        period: str,
        version: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """BROKEN: Ignores version check and returns mutable internal dict reference."""
        return self._entries.get((tenant_id, period))

    def set(
        self,
        tenant_id: str,
        period: str,
        invoice: Dict[str, Any],
        version: Optional[int] = None,
    ) -> None:
        """BROKEN: Ignores version and stores mutable caller dict directly."""
        self._entries[(tenant_id, period)] = invoice

    def invalidate(self, tenant_id: str, period: Optional[str] = None) -> int:
        """BROKEN: Fails to clear all tenant periods when period is None."""
        removed = self._entries.pop((tenant_id, period), None)
        return 1 if removed is not None else 0

    def clear(self) -> None:
        """Clear all entries from the cache."""
        self._entries.clear()
