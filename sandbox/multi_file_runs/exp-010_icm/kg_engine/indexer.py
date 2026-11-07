"""In-Memory Inverted Index."""
from typing import Dict, List, Set


class InvertedIndex:
    """Maintains term-to-document postings with atomic cleanup."""

    def __init__(self) -> None:
        self.postings: Dict[str, Set[str]] = {}
        self.doc_lengths: Dict[str, int] = {}

    def index_document(self, doc_id: str, tokens: List[str]) -> None:
        self.doc_lengths[doc_id] = len(tokens)
        for t in set(tokens):
            if t not in self.postings:
                self.postings[t] = set()
            self.postings[t].add(doc_id)

    def delete_document(self, doc_id: str) -> None:
        """Removes document length record and prunes postings completely."""
        if doc_id in self.doc_lengths:
            del self.doc_lengths[doc_id]
        for term, doc_set in list(self.postings.items()):
            doc_set.discard(doc_id)
            if not doc_set:
                del self.postings[term]

    def search(self, term: str) -> Set[str]:
        return set(self.postings.get(term, set()))
