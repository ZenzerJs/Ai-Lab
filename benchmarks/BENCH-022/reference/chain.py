"""RuleChain: ordered rules with deny precedence.

Every matching rule contributes; DENY wins over ALLOW regardless of the
order rules were declared. With no matching rule the chain returns its
configured default.
"""
from models import Decision, Rule


class RuleChain:
    def __init__(self, rules, default=Decision.ALLOW):
        self.rules = list(rules)
        if isinstance(default, str):
            default = Decision(default)
        if not isinstance(default, Decision):
            raise ValueError("default must be a Decision")
        self.default = default

    def decide(self, subject):
        """Deny precedence: a matching DENY outranks every ALLOW."""
        matched = [r.action for r in self.rules if r.matches(subject)]
        if not matched:
            return self.default
        if Decision.DENY in matched:
            return Decision.DENY
        return Decision.ALLOW

    def explain(self, subject):
        """(decision, matching patterns) for audit output."""
        hits = [r for r in self.rules if r.matches(subject)]
        return self.decide(subject), [r.pattern for r in hits]
