"""All-or-nothing multi-bucket consumption."""
from models import as_decimal


class RateLimiter:
    def __init__(self, registry):
        self.registry = registry

    def consume(self, tenant_id, requests):
        totals = {}
        for name, amount in requests:
            amount = as_decimal(amount)
            if amount == 0:
                raise ValueError("amount must be positive")
            totals[name] = totals.get(name, 0) + amount
        buckets = {name: self.registry.get(tenant_id, name) for name in totals}
        if not buckets:
            return True
        snapshots = {
            name: (bucket.state.tokens, bucket.state.updated_at)
            for name, bucket in buckets.items()
        }
        committed = False
        try:
            now = self.registry.clock()
            for bucket in buckets.values():
                bucket.refill(now)
            if any(buckets[name].state.tokens < amount for name, amount in totals.items()):
                return False
            for name, amount in totals.items():
                buckets[name].state.tokens -= amount
            committed = True
            return True
        finally:
            if not committed:
                for name, (tokens, updated_at) in snapshots.items():
                    buckets[name].state.tokens = tokens
