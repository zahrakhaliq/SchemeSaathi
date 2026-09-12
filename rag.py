import json
from pathlib import Path
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

class SchemeRetriever:
    def __init__(self, data_path):
        self.schemes = json.loads(Path(data_path).read_text(encoding="utf-8"))
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        texts = [self._to_text(s) for s in self.schemes]
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False
        ).astype("float32")

        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(embeddings)

    @staticmethod
    def _to_text(s):
        return " ".join([
            s.get("name", ""),
            s.get("category", ""),
            s.get("description", ""),
            s.get("benefits", ""),
            " ".join(s.get("eligibility", [])),
            " ".join(s.get("requirements", [])),
            s.get("keywords", ""),
        ])

    def search(self, query, top_k=7, category=None):
        query = query.strip()
        if not query:
            return []

        # The category filter is intentionally applied before final ranking when a
        # strong user intent was inferred. This prevents unrelated schemes such as
        # agricultural loans from appearing for a student asking about tuition fees.
        q = self.model.encode(
            [query],
            normalize_embeddings=True,
            show_progress_bar=False
        ).astype("float32")

        scores, indices = self.index.search(
            q, len(self.schemes)
        )

        results = []
        for score, idx in zip(scores[0], indices[0]):
            item = self.schemes[int(idx)]

            if category and item["category"].lower() != category.lower():
                continue

            semantic_score = float(score)
            if semantic_score < 0.20:
                continue

            # Small lexical boost for exact user-need terms. This makes phrases such
            # as "tuition fee" and "tractor subsidy" more decisive than broad words
            # such as "financial help".
            haystack = self._to_text(item).lower()
            query_terms = [t for t in query.lower().split() if len(t) >= 4]
            lexical_hits = sum(1 for term in query_terms if term in haystack)
            final_score = semantic_score + min(0.10, lexical_hits * 0.015)

            results.append((item, final_score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def browse(self, category=None, top_k=100):
        items = self.schemes
        if category:
            items = [s for s in items if s["category"].lower() == category.lower()]
        return [(s, 1.0) for s in items[:top_k]]
