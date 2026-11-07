"""Test suite for EXP-011 Policy API Gateway."""
import time
from gateway.billing import BillingEngine
from gateway.limiter import SlidingWindowLimiter
from gateway.router import RequestRouter
from gateway.webhook import WebhookVerifier


def test_router_middleware_execution():
    router = RequestRouter()

    def add_auth(req):
        req["auth_tenant"] = "tenant_test"
        return req

    router.use(add_auth)
    router.route("/v1/ping", lambda r: {"status": 200, "tenant": r.get("auth_tenant")})

    res = router.handle({"path": "/v1/ping"})
    assert res["status"] == 200
    assert res["tenant"] == "tenant_test"


def test_webhook_signing_roundtrip():
    verifier = WebhookVerifier(secret="supersecret")
    payload = b'{"event":"charge.succeeded"}'
    ts = 1700000000
    sig = verifier.sign(payload, ts)

    assert isinstance(sig, str)
    assert len(sig) == 64


def test_webhook_verification_constant_time():
    verifier = WebhookVerifier(secret="secret_key", tolerance_seconds=60.0)
    payload = b'{"tenant":"acme","action":"deploy"}'
    now = int(time.time())
    sig = verifier.sign(payload, now)

    assert verifier.verify(payload, now, sig) is True
    bad_sig = sig[:-1] + ("0" if sig[-1] != "0" else "1")
    assert verifier.verify(payload, now, bad_sig) is False
    assert verifier.verify(payload, now - 120, sig) is False


def test_rate_limiter_strict_burst_boundary():
    limiter = SlidingWindowLimiter(max_requests=5, window_seconds=10.0)
    now = 1000.0

    for _ in range(5):
        assert limiter.allow("t1", now=now) is True

    assert limiter.allow("t1", now=now) is False
    assert limiter.allow("t1", now=now + 15.0) is True


def test_billing_within_quota():
    engine = BillingEngine()
    cost = engine.calculate_cost("pro", 50000)
    assert cost == 0.0


def test_billing_fractional_overage_threshold():
    engine = BillingEngine()
    cost = engine.calculate_cost("pro", 100500)
    assert cost == 0.05
    assert engine.calculate_cost("pro", 100000) == 0.0
