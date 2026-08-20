"""Embedding layer (Phase 8.8.5).

Small, framework-independent embedding abstraction with two concrete
implementations:

* :class:`FastEmbedEmbedder` — real production embeddings via the
  already-installed ``fastembed`` package (default model:
  ``sentence-transformers/all-MiniLM-L6-v2``, 384-dim, ONNX runtime).
  Runs locally, no API key required. The model is downloaded on
  first use and cached at ``~/.cache/fastembed``.

* :class:`HashingFallbackEmbedder` — deterministic, dependency-light
  fallback used by the CI test suite and by degraded-mode operation
  (no model available, no network). Same text → same vector, no
  external calls, no model download.

No cosine similarity, no vector store, no retrieval logic lives in
this module — those arrive in later phases. This module only turns
strings into normalized float vectors.
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from typing import Iterable, Sequence

import numpy as np


DEFAULT_FASTEMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Known-dimension lookup so `FastEmbedEmbedder.dimension` is available
# without a model download. If the caller configures a model not in
# this table, dimension is discovered lazily from the first embed call.
_KNOWN_FASTEMBED_DIMENSIONS: dict[str, int] = {
    "sentence-transformers/all-MiniLM-L6-v2": 384,
    "BAAI/bge-small-en-v1.5": 384,
    "BAAI/bge-base-en-v1.5": 768,
}


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------


class Embedder(ABC):
    """Turn a batch of texts into a batch of same-length float vectors.

    Implementations MUST:
      * accept a batch and return one vector per input, in the same order
      * expose a stable :attr:`dimension` property
      * normalize their output to unit length (cosine-similarity ready)
      * raise :class:`ValueError` on empty input list or on any empty string
    """

    @property
    @abstractmethod
    def dimension(self) -> int:  # pragma: no cover - abstract
        ...

    @abstractmethod
    def embed(self, texts: Sequence[str]) -> list[list[float]]:  # pragma: no cover
        ...


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _validate_batch(texts: Sequence[str]) -> None:
    """Common input validation used by both concrete embedders."""
    if not isinstance(texts, Sequence) or isinstance(texts, str):
        raise ValueError(
            "Embedder.embed expects a Sequence of strings, not a single string."
        )
    if len(texts) == 0:
        raise ValueError("Embedder.embed requires at least one input text.")
    for i, t in enumerate(texts):
        if not isinstance(t, str):
            raise ValueError(f"Input at index {i} is not a string: {type(t).__name__}")
        if len(t.strip()) == 0:
            raise ValueError(f"Input at index {i} is empty or whitespace-only.")


def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    """L2-normalize every row of ``matrix`` in-place-safe fashion.

    Zero-norm rows are returned unchanged (all zeros) rather than
    NaN-ed by a divide-by-zero. Cosine similarity against a zero
    vector will simply be 0, which is the honest answer.
    """
    if matrix.ndim != 2:
        raise ValueError(
            f"_normalize_rows expects a 2-D matrix, got shape {matrix.shape}"
        )
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    safe_norms = np.where(norms == 0, 1.0, norms)
    return matrix / safe_norms


# ---------------------------------------------------------------------------
# HashingFallbackEmbedder — deterministic, no model, no network.
# ---------------------------------------------------------------------------


class HashingFallbackEmbedder(Embedder):
    """Deterministic embedder for tests and degraded operation.

    The vector for a given text is derived by seeding a numpy random
    generator with ``sha256(text)``, drawing ``dimension`` samples from
    a standard normal distribution, and L2-normalizing the result.
    This gives:

      * ``embed(["hello"]) == embed(["hello"])`` — bit-exact
      * different texts → almost-always distinct vectors
      * unit-length vectors ready for cosine similarity
      * no I/O, no model download, no external service

    NOT a substitute for FastEmbed in production — semantic similarity
    is meaningless with a hash-seeded random draw. The point is
    determinism for testing, not retrieval quality.
    """

    def __init__(self, dimension: int = 128):
        if dimension <= 0:
            raise ValueError("dimension must be positive.")
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        _validate_batch(texts)
        rows = np.stack([self._embed_one(t) for t in texts], axis=0)
        normalized = _normalize_rows(rows)
        return normalized.tolist()

    def _embed_one(self, text: str) -> np.ndarray:
        # SHA-256 → 32 bytes → truncate to 8 bytes of little-endian
        # unsigned int → numpy SeedSequence for a stable, spread seed.
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], byteorder="little", signed=False)
        rng = np.random.default_rng(seed)
        return rng.standard_normal(self._dimension).astype(np.float32)


# ---------------------------------------------------------------------------
# FastEmbedEmbedder — real production embeddings.
# ---------------------------------------------------------------------------


class FastEmbedEmbedder(Embedder):
    """Production embedder backed by ``fastembed`` (ONNX runtime).

    The model is instantiated **lazily** on the first :meth:`embed`
    call, so importing this class is cheap and creating one at
    dependency-wiring time does not trigger a model download.
    """

    def __init__(self, model_name: str = DEFAULT_FASTEMBED_MODEL):
        if not isinstance(model_name, str) or not model_name.strip():
            raise ValueError("model_name must be a non-empty string.")
        self._model_name = model_name
        self._model = None  # lazy — first embed() call constructs it
        self._known_dimension = _KNOWN_FASTEMBED_DIMENSIONS.get(model_name)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimension(self) -> int:
        if self._known_dimension is not None:
            return self._known_dimension
        # For an unknown model, force a lazy init and probe with a
        # single-token embedding to discover the dimension.
        self._ensure_model()
        vec = self._call_model(["a"])
        self._known_dimension = vec.shape[1]
        return self._known_dimension

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        _validate_batch(texts)
        self._ensure_model()
        matrix = self._call_model(list(texts))
        # fastembed's all-MiniLM outputs are already unit-normalized,
        # but we normalize defensively so contract holds for every
        # possible backing model.
        normalized = _normalize_rows(matrix)
        return normalized.tolist()

    def _ensure_model(self) -> None:
        if self._model is not None:
            return
        # Local import so nothing outside fastembed's package is loaded
        # unless a real embedding is actually required.
        from fastembed import TextEmbedding  # type: ignore[import-untyped]

        self._model = TextEmbedding(model_name=self._model_name)

    def _call_model(self, texts: list[str]) -> np.ndarray:
        assert self._model is not None
        # TextEmbedding.embed returns an iterable of numpy arrays.
        iterable: Iterable[np.ndarray] = self._model.embed(texts)
        vectors = [np.asarray(v, dtype=np.float32) for v in iterable]
        if len(vectors) != len(texts):
            raise RuntimeError(
                f"fastembed returned {len(vectors)} vectors for {len(texts)} inputs."
            )
        return np.stack(vectors, axis=0)


__all__ = [
    "DEFAULT_FASTEMBED_MODEL",
    "Embedder",
    "FastEmbedEmbedder",
    "HashingFallbackEmbedder",
]
