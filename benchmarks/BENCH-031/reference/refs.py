"""Named references and HEAD."""


class RefStore:
    """ref name -> commit oid; HEAD may name a branch or be detached."""

    def __init__(self):
        self.refs = {}
        self.head = "main"    # ref name when attached, oid when detached

    def set(self, name: str, oid: str) -> None:
        self.refs[name] = oid

    def get(self, name: str):
        return self.refs.get(name)

    def head_oid(self):
        """Commit oid HEAD resolves to (through the branch ref)."""
        return self.refs.get(self.head)

    def advance_head(self, oid: str) -> None:
        """Point the current branch ref at oid."""
        self.refs[self.head] = oid
