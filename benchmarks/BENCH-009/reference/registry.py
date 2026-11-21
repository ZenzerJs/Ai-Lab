"""Tenant-scoped bucket ownership."""
import time

from bucket import TokenBucket


class BucketRegistry:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self._buckets = {}

    def add(self, tenant_id, name, capacity, refill_rate):
        key = (tenant_id, name)
        if key in self._buckets:
            raise ValueError("duplicate bucket")
        bucket = TokenBucket(capacity, refill_rate, self.clock)
        self._buckets[key] = bucket
        return bucket

    def get(self, tenant_id, name):
        return self._buckets[(tenant_id, name)]
