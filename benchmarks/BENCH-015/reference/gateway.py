"""Verified webhook ingress with idempotent processing."""
import hashlib

from models import ConflictError, Delivery, Receipt, SignatureError


class WebhookGateway:
    def __init__(self, signer, store):
        self.signer = signer
        self.store = store
        self._receipts = {}

    def receive(self, event_id, payload, timestamp, signature, idempotency_key):
        delivery = Delivery(event_id, payload, timestamp, signature)
        if not self.signer.verify(delivery.payload, delivery.timestamp, delivery.signature):
            raise SignatureError("signature verification failed")
        digest = hashlib.sha256(delivery.payload).hexdigest()
        status = self.store.record(idempotency_key, digest)
        if status == self.store.CONFLICT:
            raise ConflictError("idempotency key reused with a different payload")
        if status == self.store.DUPLICATE:
            original = self._receipts[idempotency_key]
            return Receipt(original.event_id, "duplicate", original.digest)
        receipt = Receipt(delivery.event_id, "processed", digest)
        self._receipts[idempotency_key] = receipt
        return receipt
