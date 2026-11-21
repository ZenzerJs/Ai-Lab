"""Field-allowlist enforcement over filter ASTs."""
from ast_nodes import Comparison


class Validator:
    def __init__(self, allowed_fields):
        self.allowed = frozenset(allowed_fields)

    def validate(self, node):
        if isinstance(node, Comparison) and node.field.name not in self.allowed:
            raise ValueError(f"unknown field: {node.field.name}")
        return node
