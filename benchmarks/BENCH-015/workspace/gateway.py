"""Webhook ingress with idempotent processing."""
import hashlib

from models import Delivery, Receipt, SignatureError


class WebhookGateway:
    def __init__(self, signer, store):
        self.signer = signer
        self.store = store
        self._receipts = {}

    def receive(self, event_id, payload, timestamp, signature, idempotency_key):
        delivery = Delivery(event_id, payload, timestamp, signature)
        digest = hashlib.sha256(delivery.payload).hexdigest()
        status = self.store.record(idempotency_key, digest)
        if not self.signer.verify(delivery.payload, delivery.timestamp, delivery.signature):
            raise SignatureError("signature verification failed")
        if status == self.store.CONFLICT:
            raise ValueError("idempotency key reused with a different payload")
        receipt = Receipt(delivery.event_id, "processed", digest)
        self._receipts[idempotency_key] = receipt
        return receipt
