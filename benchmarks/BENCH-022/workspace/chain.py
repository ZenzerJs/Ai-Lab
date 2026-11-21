"""RuleChain: first matching rule wins."""
from models import Decision, Rule


class RuleChain:
    def __init__(self, rules, default=Decision.ALLOW):
        self.rules = list(rules)
        self.default = default

    def decide(self, subject):
        for rule in self.rules:
            if rule.matches(subject):
                return rule.action
        return self.default

    def explain(self, subject):
        hits = [r for r in self.rules if r.matches(subject)]
        return self.decide(subject), [r.pattern for r in hits]
