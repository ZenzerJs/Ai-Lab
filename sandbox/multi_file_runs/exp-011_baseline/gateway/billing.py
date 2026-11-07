"""Tiered Usage Accounting & Overage Calculator."""
from typing import Dict


TIER_LIMITS: Dict[str, int] = {
    "free": 1000,
    "pro": 100000,
    "enterprise": 1000000,
}

OVERAGE_RATE_PER_1K: Dict[str, float] = {
    "free": 0.0,
    "pro": 0.10,
    "enterprise": 0.05,
}


class BillingEngine:
    """Calculates subscription usage and quota overage charges."""

    def calculate_cost(self, tier: str, total_units: int) -> float:
        """Calculate total overage cost using fractional accounting without truncation."""
        limit = TIER_LIMITS.get(tier, 0)
        if total_units <= limit:
            return 0.0

        overage_units = total_units - limit
        rate = OVERAGE_RATE_PER_1K.get(tier, 0.0)

        blocks = overage_units / 1000.0
        return round(blocks * rate, 4)
