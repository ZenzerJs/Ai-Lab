from bucket import TokenBucket
from registry import BucketRegistry
from middleware import RateLimiter


def test_single_bucket_smoke():
    bucket = TokenBucket(5, 1, clock=lambda: 0)
    assert bucket.consume(2, now=0)
    assert not bucket.consume(4, now=0)


def test_middleware_smoke():
    registry = BucketRegistry(clock=lambda: 0)
    registry.add("smoke", "api", 5, 0)
    assert RateLimiter(registry).consume("smoke", [("api", 2)])
