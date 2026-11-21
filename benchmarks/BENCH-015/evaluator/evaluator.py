"""Protected deterministic checks for BENCH-015."""
import hashlib
import hmac
import sys


def rejected(error, callback):
    try:
        callback()
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def run_checks():
    try:
        from models import ConflictError, Delivery, Receipt, SignatureError
        from signer import Signer
        from idempotency import IdempotencyStore
        from gateway import WebhookGateway
    except Exception as exc:
        fail("import_error", exc)

    def model_checks():
        d = Delivery("e1", b"p", 0, "sig")
        assert (d.event_id, d.payload, d.timestamp, d.signature) == ("e1", b"p", 0, "sig")
        for kw in ({"event_id": ""}, {"payload": "s"}, {"payload": "str"},
                   {"timestamp": True}, {"timestamp": -1}, {"timestamp": 1.5},
                   {"signature": ""}, {"signature": 12}):
            base = {"event_id": "e", "payload": b"x", "timestamp": 0, "signature": "s"}
            base.update(kw)
            rejected(ValueError, lambda: Delivery(**base))
        assert Receipt("e", "processed", "d").status == "processed"
        rejected(ValueError, lambda: Receipt("e", "conflict", "d"))
        assert issubclass(SignatureError, PermissionError)
        assert issubclass(ConflictError, RuntimeError)

    def signer_checks():
        signer = Signer("sekret", tolerance_seconds=300, clock=lambda: 1000)
        payload = b'{"a": 1}'
        expected_hex = hmac.new(b"sekret", b"990." + payload,
                                hashlib.sha256).hexdigest()
        sig = signer.sign(payload, 990)
        assert sig == expected_hex
        assert sig == signer.sign(payload, 990)
        assert signer.verify(payload, 990, sig)
        assert signer.verify(payload, 700, signer.sign(payload, 700))
        assert signer.verify(payload, 1300, signer.sign(payload, 1300))
        assert not signer.verify(payload, 699, signer.sign(payload, 699))
        assert not signer.verify(payload, 1301, signer.sign(payload, 1301))
        assert not signer.verify(payload, 991, sig)
        assert not signer.verify(b"tampered", 990, sig)
        assert not signer.verify(payload, 990, "0" * len(sig))
        assert not signer.verify(payload, 990, "zz" + sig[2:])
        other = Signer("other", tolerance_seconds=300, clock=lambda: 1000)
        assert not other.verify(payload, 990, sig)
        for args in (("str", 990, sig), (payload, True, sig), (payload, "990", sig),
                     (payload, 990, ""), (payload, 990, 123), (payload, 990, None),
                     (payload, 990, "éé"), (payload, 990, sig.encode())):
            assert not signer.verify(*args)
        rejected(ValueError, lambda: Signer(""))
        rejected(ValueError, lambda: Signer("k", tolerance_seconds=-1))
        rejected(ValueError, lambda: Signer("k", tolerance_seconds=True))
        rejected(ValueError, lambda: signer.sign("not-bytes", 0))
        sig2 = signer.sign(payload, 1000)
        assert sig != sig2
        assert not signer.verify(payload, 999, sig2)
        assert signer.verify(payload, 1000, sig2)
        boundary = Signer("s", tolerance_seconds=60, clock=lambda: 100)
        s = boundary.sign(payload, 40)
        assert boundary.verify(payload, 40, s)

    def idempotency_checks():
        times = [0]
        store = IdempotencyStore(clock=lambda: times[0], ttl_seconds=10)
        assert store.record("k", "d1") == "new"
        assert store.lookup("k") == "d1"
        assert store.record("k", "d1") == "duplicate"
        assert store.record("k", "d2") == "conflict"
        assert store.lookup("k") == "d1"
        times[0] = 9
        assert store.record("k", "d1") == "duplicate"
        times[0] = 11
        assert store.lookup("k") is None
        assert store.record("k", "d2") == "new"
        assert store.lookup("k") == "d2"
        store2 = IdempotencyStore(clock=lambda: 0)
        assert store2.record("a", "x") == "new"
        assert store2.record("a", "x") == "duplicate"
        assert store2.record("a", "y") == "conflict"
        assert store2.lookup("a") == "x"
        for args in (("", "d"), (None, "d"), ("k", ""), ("k", None), ("k", 5)):
            rejected(ValueError, lambda: store2.record(*args))
        rejected(ValueError, lambda: IdempotencyStore(lambda: 0, ttl_seconds=0))
        rejected(ValueError, lambda: IdempotencyStore(lambda: 0, ttl_seconds=-3))
        assert IdempotencyStore(lambda: 0).lookup("missing") is None

    def gateway_checks():
        signer = Signer("sekret", tolerance_seconds=300, clock=lambda: 1000)
        store = IdempotencyStore(clock=lambda: 1000)
        gateway = WebhookGateway(signer, store)
        payload = b'{"kind": "ping"}'
        sig = signer.sign(payload, 990)
        receipt = gateway.receive("evt-1", payload, 990, sig, "key-1")
        assert receipt.status == "processed"
        assert receipt.event_id == "evt-1"
        assert receipt.digest == hashlib.sha256(payload).hexdigest()
        dup = gateway.receive("evt-2", payload, 991, signer.sign(payload, 991), "key-1")
        assert dup.status == "duplicate" and dup.event_id == "evt-1"
        assert dup.digest == receipt.digest
        rejected(ConflictError,
                 lambda: gateway.receive("evt-3", b"other", 992, signer.sign(b"other", 992), "key-1"))
        receipt2 = gateway.receive("evt-4", b"other", 993, signer.sign(b"other", 993), "key-2")
        assert receipt2.status == "processed" and receipt2.event_id == "evt-4"
        assert store.lookup("key-1") == receipt.digest
        bad = WebhookGateway(signer, IdempotencyStore(clock=lambda: 1000))
        rejected(SignatureError, lambda: bad.receive("e", payload, 990, "deadbeef", "bk"))
        rejected(SignatureError, lambda: bad.receive("e", payload, 100, signer.sign(payload, 100), "bk"))
        rejected(SignatureError, lambda: bad.receive("e", payload, 990, signer.sign(b"x", 990), "bk"))
        assert bad.store.lookup("bk") is None
        receipt3 = bad.receive("e", payload, 990, sig, "bk")
        assert receipt3.status == "processed"
        for args in (("e", b"p", -1, "s", "k"), ("e", b"p", True, "s", "k"),
                     ("", b"p", 0, "s", "k"), ("e", "s", 0, "s", "k"),
                     ("e", b"p", 0, "", "k")):
            rejected(ValueError, lambda: gateway.receive(*args))

    for check in (model_checks, signer_checks, idempotency_checks, gateway_checks):
        try:
            check()
        except Exception as exc:
            fail("webhook_invariant_violation",
                 f"{check.__name__}: {type(exc).__name__}: {exc}")
    print("ALL CHECKS PASSED")


def fail(reason, detail):
    print(f"REASON: {reason}", file=sys.stderr)
    print(detail, file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    run_checks()
