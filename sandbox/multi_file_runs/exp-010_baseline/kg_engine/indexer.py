"""In-Memory Inverted Index."""
from typing import Dict, List, Set


class InvertedIndex:
    """Maintains term-to-document postings."""

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
        """Remove document and scrub doc_id from postings."""
        if doc_id in self.doc_lengths:
            del self.doc_lengths[doc_id]
        empty_terms = []
        for term, doc_ids in self.postings.items():
            doc_ids.discard(doc_id)
            if not doc_ids:
                empty_terms.append(term)
        for term in empty_terms:
            del self.postings[term]
