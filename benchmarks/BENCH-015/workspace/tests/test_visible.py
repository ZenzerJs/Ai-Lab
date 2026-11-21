from signer import Signer
from idempotency import IdempotencyStore
from gateway import WebhookGateway


def test_receive_smoke():
    signer = Signer("sekret", tolerance_seconds=300, clock=lambda: 1000)
    store = IdempotencyStore(clock=lambda: 1000)
    gateway = WebhookGateway(signer, store)
    payload = b'{"kind": "ping"}'
    sig = signer.sign(payload, 990)
    receipt = gateway.receive("evt-1", payload, 990, sig, "key-1")
    assert receipt.status == "processed"
