"""Environment."""
from models import EvalError


class Environment:
    def __init__(self, parent=None):
        self.parent = parent
        self.bindings = {}

    def define(self, name, value):
        self.bindings[name] = value

    def get(self, name):
        return self.bindings[name]   # KeyError on missing

    def has(self, name):
        return name in self.bindings

    def child(self):
        return Environment(self)
