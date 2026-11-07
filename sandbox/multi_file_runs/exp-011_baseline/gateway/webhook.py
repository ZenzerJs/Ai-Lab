"""Cryptographic Webhook Dispatcher & Verifier."""
import hashlib
import hmac
import time
from typing import Optional


class WebhookVerifier:
    """Verifies HMAC SHA-256 signatures on inbound webhooks."""

    def __init__(self, secret: str, tolerance_seconds: float = 300.0) -> None:
        self.secret = secret
        self.tolerance_seconds = tolerance_seconds

    def sign(self, payload: bytes, timestamp: int) -> str:
        msg = f"{timestamp}.".encode("utf-8") + payload
        return hmac.new(self.secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()

    def verify(self, payload: bytes, header_timestamp: int, signature: str) -> bool:
        """Verify HMAC signature using constant-time comparison."""
        now = int(time.time())
        if abs(now - header_timestamp) > self.tolerance_seconds:
            return False

        expected = self.sign(payload, header_timestamp)
        return hmac.compare_digest(signature, expected)
