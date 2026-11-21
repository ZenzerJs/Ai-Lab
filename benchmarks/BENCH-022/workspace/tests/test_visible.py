from clock import ManualClock
from limiter import RateLimiter
from models import Decision, Quota
from chain import RuleChain, Rule


def test_limiter_smoke():
    lim = RateLimiter([Quota("q", 2, 60.0)], ManualClock())
    assert lim.allow("a") is Decision.ALLOW
    assert lim.allow("a") is Decision.ALLOW
    assert lim.allow("a") is Decision.DENY


def test_chain_smoke():
    chain = RuleChain([Rule("*", "allow"), Rule("api:*", "deny")])
    assert chain.decide("api:x") is Decision.DENY
