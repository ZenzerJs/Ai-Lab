"""Okapi BM25 Ranking Engine."""
import math
from typing import Dict, List


class BM25Ranker:
    """Computes BM25 relevance scores for document queries."""

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
        """Compute BM25 score resilient to zero-division edge cases."""
        doc_len = len(doc_terms)
        score = 0.0

        for term in query_terms:
            df = doc_freqs.get(term, 0)
            if df == 0:
                continue

            # Standard Robertson-Spärck Jones IDF
            idf = math.log((total_docs - df + 0.5) / (df + 0.5) + 1.0)
            tf = doc_terms.count(term)

            len_norm = 1.0 - self.b + self.b * (doc_len / avg_doc_len if avg_doc_len > 0 else 1.0)
            denom = tf + self.k1 * len_norm
            term_score = (idf * (tf * (self.k1 + 1.0)) / denom) if denom > 0 else 0.0
            score += term_score

        return score
