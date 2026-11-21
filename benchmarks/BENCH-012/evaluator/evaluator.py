"""Protected deterministic checks for BENCH-012."""
import sys


def rejected(error, callback):
    try:
        callback()
    except error:
        return
    raise AssertionError(f"expected {error.__name__}")


def run_checks():
    try:
        from models import Role, Rule, Decision
        from matcher import matches, valid_resource
        from policy_engine import PolicyEngine
        from audit import AuditLog

        parents = ["base"]
        role = Role("child", parents)
        parents.append("other")
        assert role.parents == ("base",)
        rejected(ValueError, lambda: Rule("r", "read", "*", "maybe"))
        rejected(ValueError, lambda: PolicyEngine([Role("r"), Role("r")], []))
        for path in ("docs/a", "docs/a/b", "docs-secret/x", "a_b/v1.2-file"):
            assert valid_resource(path)
        assert matches("docs/*", "docs/a") and matches("docs/*", "docs/a/b")
        for path in ("docs", "docs-secret/x", "docs2/x"):
            assert not matches("docs/*", path)
        assert matches("docs/a", "docs/a") and not matches("docs/a", "docs/ab")
        for path in ("", ".", "..", "docs/../secret", "docs/./a", "/docs/a",
                     "docs//a", "docs/a/", "docs/..", "docs/%2e%2e/a",
                     "docs/%252e%252e/a", "docs\\..\\secret", "docs/a?x=1",
                     "docs/a#frag", "docs/*"):
            assert not valid_resource(path)
            assert not matches("*", path)
            assert not matches("docs/*", path)
        for pattern in ("docs*", "docs/**", "*/a", "docs/../*", "docs//*"):
            assert not matches(pattern, "docs/a")

        rules = [Rule("reader", "read", "docs/*"), Rule("reader", "read", "docs/private/*", "deny")]
        for ordered in (rules, list(reversed(rules))):
            engine = PolicyEngine([Role("reader")], ordered)
            assert engine.decide("u", ["reader"], "read", "docs/private/a") == Decision(False, "explicit_deny")
            assert engine.decide("u", ["reader"], "read", "docs/public/a") == Decision(True, "allow")
            assert engine.decide("u", ["reader"], "write", "docs/public/a") == Decision(False, "no_matching_allow")

        roles = [Role("child", ["parent"]), Role("parent", ["base"]), Role("base", ["child"])]
        rules = [Rule("child", "*", "docs/*"), Rule("base", "read", "docs/private/*", "deny"),
                 Rule("parent", "read", "images/*")]
        engine = PolicyEngine(roles, rules)
        assert engine.resolve_roles(["child", "missing"]) == {"child", "parent", "base"}
        assert engine.resolve_roles([]) == set()
        assert engine.decide("u", ["child"], "read", "docs/private/a") == Decision(False, "explicit_deny")
        assert engine.decide("u", ["child"], "read", "images/a").allowed
        assert engine.decide("u", ["child"], "write", "docs/public/a").allowed
        assert PolicyEngine([Role("self", ["self", "unknown"])], []).resolve_roles(["self"]) == {"self"}
        for requested in (["permit", "block"], ["block", "permit"]):
            engine2 = PolicyEngine([Role("permit"), Role("block")],
                                   [Rule("permit", "*", "*"), Rule("block", "*", "*", "deny")])
            assert engine2.decide("u", requested, "read", "a").reason == "explicit_deny"

        log = AuditLog()
        engine = PolicyEngine([Role("r")], [Rule("r", "read", "docs/*"),
                                            Rule("r", "read", "docs/secret", "deny")], log)
        cases = [(["r"], "docs/a", True, "allow"),
                 (["r"], "docs/secret", False, "explicit_deny"),
                 ([], "docs/a", False, "no_matching_allow"),
                 (["unknown"], "docs/a", False, "no_matching_allow"),
                 (["r"], "docs/../secret", False, "invalid_resource"),
                 (["r"], "docs-secret/a", False, "no_matching_allow")]
        expected = []
        for names, resource, allowed, reason in cases:
            assert engine.decide("alice", iter(names), "read", resource) == Decision(allowed, reason)
            expected.append({"subject": "alice", "roles": names, "action": "read",
                             "resource": resource, "allowed": allowed, "reason": reason})
        assert log.entries() == expected
        returned = log.entries()
        returned[0]["roles"].append("mutated")
        returned[0]["reason"] = "changed"
        assert log.entries() == expected
        roles_input = ["r"]
        log.record("manual", roles_input, "read", "a", Decision(False, "manual"))
        roles_input.append("changed")
        assert log.entries()[-1]["roles"] == ["r"]
        assert AuditLog().entries() == []
        assert PolicyEngine([], []).audit.entries() == []
    except Exception as exc:
        print("REASON: rbac_invariant_violation", file=sys.stderr)
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    run_checks()
