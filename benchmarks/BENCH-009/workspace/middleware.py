"""Sequential rate-limit request adapter."""
class RateLimiter:
    def __init__(self, registry):
        self.registry = registry

    def consume(self, tenant_id, requests):
        for name, amount in requests:
            if not self.registry.get(tenant_id, name).consume(amount):
                return False
        return True
