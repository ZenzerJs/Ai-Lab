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
    ts = int(time.time())
    sig = verifier.sign(payload, ts)

    assert isinstance(sig, str)
    assert len(sig) == 64
    # Valid verification
    assert verifier.verify(payload, ts, sig) is True
    # Tampered signature
    assert verifier.verify(payload, ts, sig[:-1] + "0") is False


def test_billing_within_and_over_quota():
    engine = BillingEngine()
    # Within quota
    assert engine.calculate_cost("pro", 50000) == 0.0
    # Over quota with exact fractional overage
    # Pro limit: 100,000. 100,500 units = 500 units overage = 0.5 blocks * $0.10 = $0.05
    assert engine.calculate_cost("pro", 100500) == 0.05
    # Enterprise limit: 1,000,000. 1,002,000 = 2,000 units overage = 2.0 blocks * $0.05 = $0.10
    assert engine.calculate_cost("enterprise", 1002000) == 0.10


def test_sliding_window_limiter_strict_burst():
    limiter = SlidingWindowLimiter(max_requests=3, window_seconds=60.0)
    now = 1000.0

    assert limiter.allow("t1", now=now) is True
    assert limiter.allow("t1", now=now + 1.0) is True
    assert limiter.allow("t1", now=now + 2.0) is True
    # 4th request must be rejected (no off-by-one leak)
    assert limiter.allow("t1", now=now + 3.0) is False
