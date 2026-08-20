"""In-memory NumPy cosine vector store (Phase 8.8.6).

Holds the corpus of :class:`KnowledgeChunk` objects alongside their
embedding vectors, and answers top-k cosine-similarity queries.

Chosen deliberately over FAISS / Chroma / an external vector DB —
for a ~50-chunk clinic corpus (Phase 8.8.4 produced 42), a numpy
matrix multiply is faster than any wire hop and easier to test.
The public shape (``fit`` / ``search`` / :class:`VectorSearchResult`)
was picked so a future swap to a heavier backend touches only this
module.

No embeddings are computed here — this module takes pre-computed
vectors and does the geometry. Embedding is
:class:`app.rag.embedder.Embedder`'s job; wiring the two together is
Phase 8.8.7's job (Retriever). This module knows nothing about
either.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
from pydantic import BaseModel, Field

from app.rag.chunker import KnowledgeChunk


# ---------------------------------------------------------------------------
# Result model
# ---------------------------------------------------------------------------


class VectorSearchResult(BaseModel):
    """One search hit — the retrieved chunk plus its cosine similarity."""

    chunk: KnowledgeChunk
    score: float = Field(..., ge=-1.0, le=1.0)

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class NumpyVectorStore:
    """Fit-once, search-many in-memory cosine index.

    Deterministic behaviour:
      * :meth:`fit` L2-normalizes every row defensively, so cosine
        similarity is a plain dot product at query time.
      * :meth:`search` uses ``numpy.argsort(kind="stable")`` so ties
        fall back to original corpus order — reproducible across
        runs and platforms.
    """

    def __init__(self) -> None:
        self._chunks: list[KnowledgeChunk] = []
        self._matrix: np.ndarray | None = None
        self._dimension: int | None = None

    # -- introspection -------------------------------------------------------

    @property
    def size(self) -> int:
        return len(self._chunks)

    @property
    def dimension(self) -> int | None:
        return self._dimension

    @property
    def is_fitted(self) -> bool:
        return self._matrix is not None and self._matrix.size > 0

    # -- fit -----------------------------------------------------------------

    def fit(
        self,
        chunks: Sequence[KnowledgeChunk],
        vectors: Sequence[Sequence[float]],
    ) -> None:
        """Populate the store with a chunk/vector corpus.

        Both sides must be non-empty and the same length; every
        vector must be finite and share the same dimensionality.
        """
        if len(chunks) == 0:
            raise ValueError("fit requires a non-empty chunk corpus.")
        if len(chunks) != len(vectors):
            raise ValueError(
                f"chunks / vectors length mismatch: {len(chunks)} vs {len(vectors)}"
            )

        try:
            matrix = np.asarray(vectors, dtype=np.float32)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"vectors are not a rectangular numeric array: {exc}") from exc

        if matrix.ndim != 2:
            raise ValueError(
                f"vectors must form a 2-D matrix; got shape {matrix.shape}"
            )
        if matrix.shape[1] == 0:
            raise ValueError("vectors must have at least one dimension.")
        if not np.all(np.isfinite(matrix)):
            raise ValueError("vectors contain NaN or infinite values.")

        # Row-wise L2 normalize so cosine similarity is a dot product.
        # Zero-norm rows stay zero (cosine similarity 0) rather than
        # NaN-ing the division.
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        safe = np.where(norms == 0, 1.0, norms)
        normalized = matrix / safe

        self._matrix = normalized.astype(np.float32, copy=False)
        self._chunks = list(chunks)
        self._dimension = int(matrix.shape[1])

    # -- search --------------------------------------------------------------

    def search(
        self,
        query_vector: Sequence[float],
        top_k: int = 4,
    ) -> list[VectorSearchResult]:
        """Return the top-k most cosine-similar chunks to
        ``query_vector``, sorted highest similarity first.

        If ``top_k`` exceeds the corpus size, the entire corpus is
        returned. Ties in similarity break by original corpus index
        (stable sort).
        """
        if self._matrix is None:
            raise RuntimeError("NumpyVectorStore.search called before fit().")
        if not isinstance(top_k, int) or isinstance(top_k, bool):
            raise ValueError("top_k must be an int.")
        if top_k <= 0:
            raise ValueError("top_k must be > 0.")

        q = self._prepare_query(query_vector)

        # Cosine similarity = dot product (rows and query are unit-normalized).
        scores = self._matrix @ q
        # argsort ascending + reverse gives descending. Using stable
        # sort with a negated key preserves original order on ties.
        order = np.argsort(-scores, kind="stable")
        k = min(top_k, len(self._chunks))
        selected = order[:k]

        return [
            VectorSearchResult(chunk=self._chunks[int(i)], score=float(scores[int(i)]))
            for i in selected
        ]

    # -- internals -----------------------------------------------------------

    def _prepare_query(self, query_vector: Sequence[float]) -> np.ndarray:
        assert self._dimension is not None  # is_fitted implied by caller

        try:
            q = np.asarray(query_vector, dtype=np.float32)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"query_vector is not a numeric sequence: {exc}") from exc

        if q.ndim != 1:
            raise ValueError(
                f"query_vector must be 1-D; got shape {q.shape}"
            )
        if q.shape[0] == 0:
            raise ValueError("query_vector is empty.")
        if q.shape[0] != self._dimension:
            raise ValueError(
                f"query_vector dimension {q.shape[0]} does not match "
                f"store dimension {self._dimension}."
            )
        if not np.all(np.isfinite(q)):
            raise ValueError("query_vector contains NaN or infinite values.")

        norm = float(np.linalg.norm(q))
        if norm == 0:
            raise ValueError("query_vector is a zero vector — cosine similarity is undefined.")
        return q / norm


__all__ = ["NumpyVectorStore", "VectorSearchResult"]
