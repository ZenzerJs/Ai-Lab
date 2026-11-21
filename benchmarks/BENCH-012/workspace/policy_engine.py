"""Cycle-safe inherited policy evaluation with deny precedence."""
from audit import AuditLog
from matcher import matches, valid_resource
from models import Decision


class PolicyEngine:
    def __init__(self, roles, rules, audit=None):
        self.roles = {}
        for role in roles:
            if role.name in self.roles:
                raise ValueError("duplicate role")
            self.roles[role.name] = role
        self.rules = list(rules)
        self.audit = audit if audit is not None else AuditLog()

    def resolve_roles(self, roles):
        resolved = set()
        pending = list(roles)
        while pending:
            name = pending.pop()
            if name not in self.roles:
                continue
            resolved.add(name)
            pending.extend(self.roles[name].parents)
        return resolved

    def decide(self, subject, roles, action, resource):
        roles = tuple(roles)
        if not valid_resource(resource):
            decision = Decision(False, "invalid_resource")
        else:
            resolved = self.resolve_roles(roles)
            matching = [rule for rule in self.rules
                        if rule.role in resolved
                        and rule.action in (action, "*")
                        and matches(rule.resource, resource)]
            if matching:
                decision = Decision(matching[0].effect == "allow", matching[0].effect)
            else:
                decision = Decision(False, "no_matching_allow")
        self.audit.record(subject, roles, action, resource, decision)
        return decision
