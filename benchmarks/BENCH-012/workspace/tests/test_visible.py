from models import Role, Rule
from policy_engine import PolicyEngine


def test_direct_allow():
    engine = PolicyEngine([Role("reader")], [Rule("reader", "read", "docs/*")])
    decision = engine.decide("alice", ["reader"], "read", "docs/intro")
    assert decision.allowed
    assert len(engine.audit.entries()) == 1
