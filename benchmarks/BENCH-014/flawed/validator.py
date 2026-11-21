"""Field-allowlist enforcement over filter ASTs."""
from ast_nodes import And, Comparison, Not, Or


class Validator:
    def __init__(self, allowed_fields):
        self.allowed = frozenset(allowed_fields)

    def validate(self, node):
        if isinstance(node, Comparison):
            if node.field.name not in self.allowed:
                raise ValueError(f"unknown field: {node.field.name}")
            return node
        if isinstance(node, (And, Or)):
            for child in node.children:
                self.validate(child)
            return node
        if isinstance(node, Not):
            self.validate(node.child)
            return node
        raise ValueError("expected filter node")
