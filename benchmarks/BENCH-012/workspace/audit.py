"""Independent append-only decision records."""
from copy import deepcopy


class AuditLog:
    def __init__(self):
        self._entries = []

    def record(self, subject, roles, action, resource, decision):
        if not decision.allowed:
            return
        self._entries.append(deepcopy({
            "subject": subject, "roles": list(roles), "action": action,
            "resource": resource, "allowed": decision.allowed,
            "reason": decision.reason,
        }))

    def entries(self):
        return deepcopy(self._entries)
