"""Page store for B+Tree nodes."""


class PageStore:
    def __init__(self):
        self._pages = {}
        self._counter = 0

    def allocate(self, node):
        prefix = "L" if node.is_leaf else "I"
        page_id = f"{prefix}{self._counter}"
        self._counter += 1
        self.write(page_id, node)
        return page_id

    def write(self, page_id, node):
        self._pages[page_id] = {"keys": list(node.keys)}

    def read(self, page_id):
        return self._pages[page_id]

    def dump(self):
        return dict(self._pages)
