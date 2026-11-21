"""Evaluator: walks the AST; returns each statement's value."""
from env import Environment
from lexer import tokenize
from models import Assign, Binary, EvalError, Literal, Name, Unary
from parser import Parser


def evaluate(node, env):
    if isinstance(node, Literal):
        return node.value
    if isinstance(node, Name):
        return env.get(node.ident)
    if isinstance(node, Unary):
        val = evaluate(node.operand, env)
        if node.op == "-":
            return -val
        if node.op == "+":
            return +val
        raise EvalError(f"unknown unary {node.op!r}")
    if isinstance(node, Binary):
        left = evaluate(node.left, env)
        right = evaluate(node.right, env)
        if node.op == "+":
            return left + right
        if node.op == "-":
            return left - right
        if node.op == "*":
            return left * right
        if node.op == "/":
            if right == 0:
                raise EvalError("division by zero")
            return left // right
        raise EvalError(f"unknown binary {node.op!r}")
    if isinstance(node, Assign):
        value = evaluate(node.value, env)
        env.define(node.ident, value)
        return value
    raise EvalError(f"unevaluable node {type(node).__name__}")


def run(source, env=None):
    """Tokenize, parse, and evaluate a program; returns [values]."""
    if env is None:
        env = Environment()
    stmts = Parser(tokenize(source)).parse_program()
    return [evaluate(stmt, env) for stmt in stmts]
