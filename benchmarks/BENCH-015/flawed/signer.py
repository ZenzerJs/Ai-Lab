"""HMAC-SHA256 webhook signing with replay-window tolerance."""
import hashlib
import hmac
import time


class Signer:
    def __init__(self, secret, tolerance_seconds=300, clock=time.time):
        if not isinstance(secret, str) or not secret:
            raise ValueError("secret must be a nonempty string")
        if isinstance(tolerance_seconds, bool) or not isinstance(tolerance_seconds, (int, float)) \
                or tolerance_seconds < 0:
            raise ValueError("tolerance must be a nonnegative number")
        self._key = secret.encode("utf-8")
        self.tolerance = tolerance_seconds
        self.clock = clock

    def sign(self, payload, timestamp):
        if not isinstance(payload, bytes):
            raise ValueError("payload must be bytes")
        msg = str(timestamp).encode("utf-8") + b"." + payload
        return hmac.new(self._key, msg, hashlib.sha256).hexdigest()

    def verify(self, payload, timestamp, signature):
        if not isinstance(payload, bytes):
            return False
        if isinstance(timestamp, bool) or not isinstance(timestamp, int):
            return False
        if not isinstance(signature, str) or not signature:
            return False
        now = self.clock()
        if abs(now - timestamp) >= self.tolerance:
            return False
        expected = self.sign(payload, timestamp)
        try:
            return hmac.compare_digest(signature, expected)
        except TypeError:
            return False
