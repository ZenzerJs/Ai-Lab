"""Clock-injected, decimal token bucket."""
import time

from models import BucketState, as_decimal


class TokenBucket:
    def __init__(self, capacity, refill_rate, clock=time.monotonic):
        self.clock = clock
        self.state = BucketState(capacity, refill_rate, capacity, 0)

    def refill(self, now=None):
        now = as_decimal(time.monotonic() if now is None else now)
        state = self.state
        if now >= state.updated_at:
            state.tokens = min(
                state.capacity,
                as_decimal(float(state.tokens) + float(now - state.updated_at) * float(state.refill_rate)),
            )
            state.updated_at = now

    def consume(self, amount=1, now=None):
        amount = as_decimal(amount)
        if amount == 0:
            raise ValueError("amount must be positive")
        self.refill(now)
        if self.state.tokens < amount:
            return False
        self.state.tokens -= amount
        return True
