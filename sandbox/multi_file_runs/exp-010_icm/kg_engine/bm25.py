"""Okapi BM25 Ranking Engine."""
import math
from typing import Dict, List


class BM25Ranker:
    """Computes BM25 relevance scores for document queries with zero-division protection."""

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b

    def score(
        self,
        query_terms: List[str],
        doc_terms: List[str],
        doc_freqs: Dict[str, int],
        total_docs: int,
        avg_doc_len: float,
    ) -> float:
        """
        Compute robust BM25 score. Protected against zero-division when avg_doc_len is 0
        or corpus is empty.
        """
        doc_len = len(doc_terms)
        avg_len = max(1.0, float(avg_doc_len))
        score = 0.0

        for term in query_terms:
            df = doc_freqs.get(term, 0)
            if df == 0:
                continue

            # Standard Robertson-Spärck Jones IDF
            idf = math.log((total_docs - df + 0.5) / (df + 0.5) + 1.0)
            tf = doc_terms.count(term)

            len_norm = 1.0 - self.b + self.b * (doc_len / avg_len)
            denom = tf + self.k1 * len_norm
            if denom <= 0:
                continue

            term_score = idf * (tf * (self.k1 + 1.0)) / denom
            score += term_score

        return score
