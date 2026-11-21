"""HMAC-SHA256 webhook signing."""
import hashlib
import hmac
import time


class Signer:
    def __init__(self, secret, tolerance_seconds=300, clock=time.time):
        self._key = secret.encode("utf-8")
        self.tolerance = tolerance_seconds
        self.clock = clock

    def sign(self, payload, timestamp):
        return hmac.new(self._key, payload, hashlib.sha256).hexdigest()

    def verify(self, payload, timestamp, signature):
        expected = self.sign(payload, timestamp)
        return signature == expected
