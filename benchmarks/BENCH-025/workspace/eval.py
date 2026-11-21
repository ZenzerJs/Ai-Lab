"""Evaluator."""
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
        return -val if node.op == "-" else val
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
            return left / right   # float, unguarded
        raise EvalError("unknown op")
    if isinstance(node, Assign):
        value = evaluate(node.value, env)
        env.define(node.ident, value)
        return value
    raise EvalError("unevaluable")


def run(source, env=None):
    if env is None:
        env = Environment()
    stmts = Parser(tokenize(source)).parse_program()
    return [evaluate(stmt, env) for stmt in stmts]
