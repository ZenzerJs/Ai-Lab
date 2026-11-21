"""Parameterized SQL generation for validated filter ASTs."""
from ast_nodes import And, Comparison, Not, Or
from validator import Validator


class SQLCompiler:
    def __init__(self, allowed_fields):
        self.validator = Validator(allowed_fields)

    def compile(self, node):
        params = []
        sql = self._emit(node, params)
        return sql, params

    def _emit(self, node, params):
        if isinstance(node, Comparison):
            params.append(node.literal.value)
            op = "LIKE" if node.op == "like" else node.op
            return f"{node.field.name} {op} ?"
        if isinstance(node, (And, Or)):
            sep = " AND " if isinstance(node, And) else " OR "
            return "(" + sep.join(self._emit(child, params) for child in node.children) + ")"
        if isinstance(node, Not):
            return "NOT (" + self._emit(node.child, params) + ")"
        raise ValueError("expected filter node")
