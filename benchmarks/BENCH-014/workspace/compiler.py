"""SQL generation for filter ASTs."""
from ast_nodes import And, Comparison, Not, Or


class SQLCompiler:
    def __init__(self, allowed_fields):
        self.allowed = allowed_fields

    def compile(self, node):
        params = []
        sql = self._emit(node, params)
        return sql, params

    def _emit(self, node, params):
        if isinstance(node, Comparison):
            if isinstance(node.literal.value, str):
                return f"{node.field.name} {node.op} '{node.literal.value}'"
            return f"{node.field.name} {node.op} {node.literal.value}"
        if isinstance(node, (And, Or)):
            sep = " AND " if isinstance(node, And) else " OR "
            return "(" + sep.join(self._emit(child, params) for child in node.children) + ")"
        if isinstance(node, Not):
            return "NOT (" + self._emit(node.child, params) + ")"
        raise ValueError("expected filter node")
