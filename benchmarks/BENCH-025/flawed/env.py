"""Lexically scoped environment with parent lookup."""
from models import EvalError


class Environment:
    def __init__(self, parent=None):
        self.parent = parent
        self.bindings = {}

    def define(self, name, value):
        self.bindings[name] = value

    def get(self, name):
        env = self
        while env is not None:
            if name in env.bindings:
                return env.bindings[name]
            env = env.parent
        raise EvalError(f"undefined name {name!r}")

    def has(self, name):
        env = self
        while env is not None:
            if name in env.bindings:
                return True
            env = env.parent
        return False

    def child(self):
        return Environment(self)
