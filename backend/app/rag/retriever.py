"""Knowledge retriever (Phase 8.8.7) — first complete pipeline.

Connects the pieces built across Phases 8.8.3-8.8.6:

    query
      -> Embedder.embed([query])
      -> query vector
      -> NumpyVectorStore.search(vector, top_k)
      -> ranked KnowledgeChunks with cosine scores

This is the last read-only building block before the Knowledge Agent.
The retriever itself carries no LLM, no natural-language formatting,
and no answer generation — those are Phase 8.8.9's job. All this
module does is take a query string and produce a ranked, provenance-
preserving list of :class:`VectorSearchResult`.

Dependencies are injected through the constructor — the retriever
never instantiates its own embedder or store, so tests can substitute
fakes without any monkey-patching.
"""

from __future__ import annotations

from typing import Sequence

from app.rag.chunker import KnowledgeChunk, chunk_documents
from app.rag.documents import KnowledgeDocument
from app.rag.embedder import Embedder
from app.rag.entity_filter import filter_and_rerank_results
from app.rag.vector_store import NumpyVectorStore, VectorSearchResult


# The approved architecture (Phase 8.8 inspection report §7) specifies
# `k=4` as the default retrieval breadth for the clinic corpus.
DEFAULT_TOP_K = 4

# Phase 8.8.14: default minimum cosine similarity a chunk must reach
# to be surfaced. `0.0` disables filtering (matches every pre-Phase-
# 8.8.14 test's expectation). Production wiring in `dependencies.py`
# overrides this from `RAG_MIN_SIMILARITY` (0.45 by default), chosen
# from measured corpus scores — see the Phase 8.8.14 report.
DEFAULT_MIN_SIMILARITY = 0.0


# Public alias — the retriever's return type IS a VectorSearchResult;
# aliasing under a domain-appropriate name makes call sites read
# naturally without introducing a second Pydantic model to maintain.
RetrievalResult = VectorSearchResult


class KnowledgeRetriever:
    """Query → ranked KnowledgeChunks pipeline.

    Constructor-injected dependencies:

    :param embedder: an :class:`Embedder` implementation used to
        vectorize the query. Must expose the SAME dimension as the
        store's fitted matrix.
    :param vector_store: a fitted :class:`NumpyVectorStore` holding
        the searchable corpus.
    :param default_top_k: how many hits to return when the caller
        doesn't override; matches the approved
        ``k = DEFAULT_TOP_K = 4`` architecture default.
    """

    def __init__(
        self,
        embedder: Embedder,
        vector_store: NumpyVectorStore,
        *,
        default_top_k: int = DEFAULT_TOP_K,
        default_min_similarity: float = DEFAULT_MIN_SIMILARITY,
    ):
        if not vector_store.is_fitted:
            raise ValueError(
                "KnowledgeRetriever requires a fitted NumpyVectorStore."
            )
        store_dim = vector_store.dimension
        if store_dim is not None and embedder.dimension != store_dim:
            raise ValueError(
                f"Embedder dimension {embedder.dimension} does not match "
                f"vector store dimension {store_dim}."
            )
        if not isinstance(default_top_k, int) or isinstance(default_top_k, bool):
            raise ValueError("default_top_k must be an int.")
        if default_top_k <= 0:
            raise ValueError("default_top_k must be > 0.")
        if not isinstance(default_min_similarity, (int, float)) or isinstance(
            default_min_similarity, bool
        ):
            raise ValueError("default_min_similarity must be a number.")
        if not -1.0 <= float(default_min_similarity) <= 1.0:
            raise ValueError(
                "default_min_similarity must be within [-1.0, 1.0] (cosine range)."
            )

        self._embedder = embedder
        self._store = vector_store
        self._default_top_k = default_top_k
        self._default_min_similarity = float(default_min_similarity)

    # -- introspection -------------------------------------------------------

    @property
    def default_top_k(self) -> int:
        return self._default_top_k

    @property
    def default_min_similarity(self) -> float:
        return self._default_min_similarity

    @property
    def corpus_size(self) -> int:
        return self._store.size

    # -- public API ----------------------------------------------------------

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        min_similarity: float | None = None,
    ) -> list[RetrievalResult]:
        """Return the top-k most relevant chunks for ``query``.

        Determinism, cosine-similarity ordering, tie-breaking, and
        top_k clamping all inherit from :class:`NumpyVectorStore`
        (Phase 8.8.6). The retriever adds query normalization,
        embedding, empty-corpus safety, and a minimum-similarity
        filter (Phase 8.8.14).

        Chunks with cosine similarity strictly below
        ``min_similarity`` (or the constructor's
        ``default_min_similarity`` when the caller doesn't override)
        are dropped from the returned list. If nothing meets the
        threshold, the return value is an empty list — the caller
        must handle that case honestly (see :class:`KnowledgeAgent`
        for the "not in knowledge base" fallback).
        """
        cleaned = self._clean_query(query)
        effective_top_k = self._effective_top_k(top_k)
        effective_min = self._effective_min_similarity(min_similarity)

        # Corpus size can never be zero here (constructor enforces
        # `is_fitted`, which requires a non-empty corpus per the
        # vector store's own fit() contract). Still handle it
        # defensively so a future change can't silently break.
        if self._store.size == 0:  # pragma: no cover - defensive
            return []

        [query_vector] = self._embedder.embed([cleaned])
        search_breadth = max(effective_top_k * 3, 12, effective_top_k)
        raw = self._store.search(
            query_vector, top_k=min(search_breadth, self._store.size)
        )
        if effective_min <= 0.0:
            candidates = raw
        else:
            candidates = [hit for hit in raw if hit.score >= effective_min]

        return filter_and_rerank_results(
            candidates,
            cleaned,
            top_k=effective_top_k,
        )

    # -- factory -------------------------------------------------------------

    @classmethod
    def build(
        cls,
        documents: Sequence[KnowledgeDocument],
        embedder: Embedder,
        *,
        default_top_k: int = DEFAULT_TOP_K,
        default_min_similarity: float = DEFAULT_MIN_SIMILARITY,
    ) -> "KnowledgeRetriever":
        """Convenience: chunk the documents, embed all chunks in one
        batch, fit a fresh :class:`NumpyVectorStore`, and return the
        wired retriever.

        Kept as a classmethod (rather than a free function) so the
        constructor-injection pattern remains the primary API — this
        is just the ergonomic wiring path for the future
        dependency-injection layer.
        """
        chunks = chunk_documents(documents)
        if not chunks:
            raise ValueError(
                "KnowledgeRetriever.build received documents that "
                "produced no chunks."
            )
        vectors = embedder.embed([c.text for c in chunks])
        store = NumpyVectorStore()
        store.fit(chunks, vectors)
        return cls(
            embedder=embedder,
            vector_store=store,
            default_top_k=default_top_k,
            default_min_similarity=default_min_similarity,
        )

    # -- internals -----------------------------------------------------------

    @staticmethod
    def _clean_query(query: str) -> str:
        if not isinstance(query, str):
            raise ValueError(
                f"query must be a string, got {type(query).__name__}."
            )
        cleaned = query.strip()
        if not cleaned:
            raise ValueError("query must not be empty or whitespace-only.")
        return cleaned

    def _effective_top_k(self, top_k: int | None) -> int:
        if top_k is None:
            return self._default_top_k
        if not isinstance(top_k, int) or isinstance(top_k, bool):
            raise ValueError("top_k must be an int.")
        if top_k <= 0:
            raise ValueError("top_k must be > 0.")
        return top_k

    def _effective_min_similarity(self, min_similarity: float | None) -> float:
        if min_similarity is None:
            return self._default_min_similarity
        if not isinstance(min_similarity, (int, float)) or isinstance(min_similarity, bool):
            raise ValueError("min_similarity must be a number.")
        value = float(min_similarity)
        if not -1.0 <= value <= 1.0:
            raise ValueError(
                "min_similarity must be within [-1.0, 1.0] (cosine range)."
            )
        return value


# Re-export what callers actually use so the future
# `app/agents/knowledge_agent.py` only needs one import.
__all__ = [
    "DEFAULT_MIN_SIMILARITY",
    "DEFAULT_TOP_K",
    "KnowledgeChunk",
    "KnowledgeRetriever",
    "RetrievalResult",
    "VectorSearchResult",
]
