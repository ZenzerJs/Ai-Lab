"""Named references and HEAD."""


class RefStore:
    def __init__(self):
        self.refs = {}
        self.head = "main"

    def set(self, name, oid):
        self.refs[name] = oid

    def get(self, name):
        return self.refs.get(name)

    def head_oid(self):
        return self.refs.get(self.head)

    def advance_head(self, oid):
        self.refs["main"] = oid   # always writes main, not current branch
