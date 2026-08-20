"""Phase 8.8.14 — RAG relevance hardening focused tests.

Five focused scenarios required by the phase spec:

  1. relevant query passes threshold           (deterministic unit test)
  2. irrelevant query rejected below threshold (deterministic unit test)
  3. KnowledgeAgent fallback on empty retrieval(deterministic unit test)
  4. doctor retrieval still works              (semantic — skipped offline)
  5. policy retrieval still works              (semantic — skipped offline)

Tests 1-3 use the ScriptedEmbedder + _tiny_store pattern from the
Phase-8.8.14 suite so they run offline in CI with zero downloads.

Tests 4-5 use FastEmbedEmbedder with skip guards: if the ONNX model
cannot be loaded (offline CI, no cache), the tests are skipped, not
failed, so the deterministic suite is never gated on network access.

Tests 6-7 are additional live-query guards (also semantic, also
skipped offline) that use the real KnowledgeAgent + RuleBasedIntentProvider
to validate the MRI rejection and positive answers end-to-end.

All assertions are against the production threshold (0.45) that ships
in config.Settings.rag_min_similarity and app.api.dependencies.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Sequence

import pytest

from app.agents.knowledge_agent import KnowledgeAgent
from app.agents.llm_provider import (
    AnswerFromContext,
    LLMProvider,
    NOT_IN_KNOWLEDGE_BASE_MESSAGE,
    RuleBasedIntentProvider,
)
from app.rag.chunker import KnowledgeChunk, chunk_documents
from app.rag.documents import DocumentLoader
from app.rag.embedder import Embedder, FastEmbedEmbedder, HashingFallbackEmbedder
from app.rag.retriever import KnowledgeRetriever
from app.rag.vector_store import NumpyVectorStore, VectorSearchResult

REAL_KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "data" / "knowledge"

# Production threshold shipped in config.Settings and .env.example.
PROD_THRESHOLD = 0.45


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


class ScriptedEmbedder(Embedder):
    """Always returns the same 2-D unit vector [1, 0] for any input.

    Used to script exact cosine scores in unit tests without network
    access or ONNX runtime.
    """

    @property
    def dimension(self) -> int:
        return 2

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


def _mk_chunk(chunk_id: str, text: str = "sample") -> KnowledgeChunk:
    return KnowledgeChunk(
        chunk_id=chunk_id,
        text=text,
        source="test.md",
        document_type="policy",
        document_id="test",
        metadata={"chunk_index": 1},
    )


def _tiny_store(scored: list[tuple[str, float]]) -> NumpyVectorStore:
    """Build a 2-D store where each chunk's cosine similarity vs [1,0]
    equals the requested score.  Identical to the helper in
    test_rag_pipeline.py — duplicated here so this module is
    self-contained and does not rely on cross-file scope."""
    chunks: list[KnowledgeChunk] = []
    vectors: list[list[float]] = []
    for cid, target in scored:
        theta = math.acos(max(min(target, 1.0), -1.0))
        vectors.append([math.cos(theta), math.sin(theta)])
        chunks.append(
            KnowledgeChunk(
                chunk_id=cid,
                text=f"content for {cid}",
                source="test.md",
                document_type="policy",
                document_id="test",
                metadata={"chunk_index": 1},
            )
        )
    store = NumpyVectorStore()
    store.fit(chunks, vectors)
    return store


class EchoProvider(LLMProvider):
    """Returns a grounded answer echoing the first context chunk."""

    def decide(self, message: str, context: Any = None) -> Any:  # pragma: no cover
        raise AssertionError("decide must not be called by KnowledgeAgent")

    def answer_from_context(
        self, question: str, context_chunks: Sequence[str]
    ) -> AnswerFromContext:
        if not context_chunks:
            return AnswerFromContext(
                answer=NOT_IN_KNOWLEDGE_BASE_MESSAGE, from_context=False
            )
        return AnswerFromContext(
            answer=f"grounded: {context_chunks[0][:80]}", from_context=True
        )


class NeverCalledProvider(LLMProvider):
    """Raises AssertionError if answer_from_context is called.

    Used to verify that KnowledgeAgent short-circuits when retrieval
    returns empty (no LLM call should happen).
    """

    def decide(self, message: str, context: Any = None) -> Any:  # pragma: no cover
        raise AssertionError

    def answer_from_context(
        self, question: str, context_chunks: Sequence[str]
    ) -> AnswerFromContext:
        raise AssertionError(
            "LLM provider must NOT be called when retrieval is filtered empty"
        )


# ---------------------------------------------------------------------------
# Fixture: FastEmbed embedder (module-scoped, skipped if model unavailable)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def fastembed() -> FastEmbedEmbedder:
    """Real 384-dim FastEmbed embedder — skipped if ONNX model is absent."""
    embedder = FastEmbedEmbedder()
    try:
        embedder._ensure_model()  # noqa: SLF001
    except Exception as exc:
        pytest.skip(
            f"FastEmbed model unavailable in this environment "
            f"(reason: {exc!r}). Semantic tests skipped."
        )
    return embedder


@pytest.fixture(scope="module")
def semantic_retriever(fastembed: FastEmbedEmbedder) -> KnowledgeRetriever:
    """Real retriever built with the production threshold (0.45)."""
    docs = DocumentLoader(REAL_KNOWLEDGE_DIR).load()
    return KnowledgeRetriever.build(
        docs,
        fastembed,
        default_min_similarity=PROD_THRESHOLD,
    )


# =============================================================================
# Test 1 — Relevant query passes threshold  (deterministic, offline)
# =============================================================================


def test_1_relevant_query_passes_threshold() -> None:
    """A chunk with similarity >= 0.45 must NOT be filtered out.

    Scenario: a query whose top hit scores 0.80 (well above threshold).
    The retriever must return it; the KnowledgeAgent must answer from it.
    """
    store = _tiny_store([("relevant_chunk", 0.80), ("noise_chunk", 0.10)])
    retriever = KnowledgeRetriever(
        ScriptedEmbedder(), store, default_min_similarity=PROD_THRESHOLD
    )
    hits = retriever.retrieve("relevant clinic question", top_k=2)
    chunk_ids = [h.chunk.chunk_id for h in hits]
    assert "relevant_chunk" in chunk_ids, (
        "A chunk scoring 0.80 must survive the 0.45 threshold filter"
    )
    assert "noise_chunk" not in chunk_ids, (
        "A chunk scoring 0.10 must be dropped by the 0.45 threshold filter"
    )
    # Scores must be correct
    passing_hit = next(h for h in hits if h.chunk.chunk_id == "relevant_chunk")
    assert passing_hit.score >= PROD_THRESHOLD


# =============================================================================
# Test 2 — Irrelevant query rejected below threshold  (deterministic, offline)
# =============================================================================


def test_2_irrelevant_query_rejected_below_threshold() -> None:
    """A query whose best matching chunk scores below 0.45 must return [].

    This is the 'MRI machine schedule' scenario in unit-test form:
    no chunk in the corpus is relevant, so the retriever must return
    an empty list rather than the nearest-but-wrong chunk.
    """
    store = _tiny_store([("clinic_hours", 0.20), ("cancellation", 0.35)])
    retriever = KnowledgeRetriever(
        ScriptedEmbedder(), store, default_min_similarity=PROD_THRESHOLD
    )
    hits = retriever.retrieve("What is the MRI machine schedule?", top_k=2)
    assert hits == [], (
        "When no chunk meets the 0.45 threshold, retrieve() must return [], "
        "not the nearest (but irrelevant) chunks"
    )


# =============================================================================
# Test 3 — KnowledgeAgent fallback on empty retrieval  (deterministic, offline)
# =============================================================================


def test_3_knowledge_agent_fallback_when_retrieval_empty() -> None:
    """KnowledgeAgent must return NOT_IN_KNOWLEDGE_BASE_MESSAGE and skip
    the LLM call when the retriever returns [] (threshold filtered everything).

    Uses NeverCalledProvider to assert no LLM call is made.
    """
    store = _tiny_store([("irrelevant_a", 0.10), ("irrelevant_b", 0.20)])
    retriever = KnowledgeRetriever(
        ScriptedEmbedder(), store, default_min_similarity=PROD_THRESHOLD
    )
    agent = KnowledgeAgent(NeverCalledProvider(), retriever)

    response = agent.handle("What is the MRI machine schedule?")

    # Honest fallback — no fabricated answer
    assert response.message == NOT_IN_KNOWLEDGE_BASE_MESSAGE, (
        "KnowledgeAgent must surface NOT_IN_KNOWLEDGE_BASE_MESSAGE when "
        "retrieval is empty; got: " + repr(response.message)
    )
    # No citations — nothing surfaced
    assert response.data["citations"] == [], (
        "No citations must be returned when retrieval is filtered empty"
    )
    # Intent preserved
    assert response.intent == "knowledge_answer"
    # Never requires staff review for knowledge paths
    assert response.requires_staff_review is False


# =============================================================================
# Test 4 — Doctor retrieval still works  (semantic, skipped offline)
# =============================================================================


@pytest.mark.parametrize(
    "query",
    [
        "Who is Dr. Ahmed?",
        "What does Dr. Ahmed specialize in?",
        "Who is Dr. Sara?",
        "What services does Dr. Sara provide?",
    ],
)
def test_4_doctor_retrieval_still_works(
    query: str, semantic_retriever: KnowledgeRetriever
) -> None:
    """Doctor queries must still surface relevant hits after threshold.

    Uses the real FastEmbed model (skipped offline). If the threshold of
    0.45 were mis-calibrated, it would reject legitimate doctor queries —
    this test catches that regression.
    """
    hits = semantic_retriever.retrieve(query, top_k=4)
    assert len(hits) >= 1, (
        f"Doctor query {query!r} returned [] — threshold may be too high "
        "or semantic embedder misconfigured"
    )
    # All returned hits must be above the production threshold
    for hit in hits:
        assert hit.score >= PROD_THRESHOLD, (
            f"Hit {hit.chunk.chunk_id!r} scored {hit.score:.4f} "
            f"but minimum is {PROD_THRESHOLD}"
        )
    # At least one doctor chunk must appear in the top results
    doc_types = {h.chunk.document_type for h in hits}
    assert "doctor" in doc_types, (
        f"No doctor chunk among the top-{len(hits)} results for {query!r}"
    )


# =============================================================================
# Test 5 — Policy retrieval still works  (semantic, skipped offline)
# =============================================================================


@pytest.mark.parametrize(
    "query",
    [
        "What is the cancellation policy?",
        "What are the clinic hours?",
        "How do I book an appointment?",
    ],
)
def test_5_policy_retrieval_still_works(
    query: str, semantic_retriever: KnowledgeRetriever
) -> None:
    """Policy / FAQ queries must still surface relevant hits after threshold.

    Same role as test_4 but for the clinic_policies.md and faq.md corpus.
    """
    hits = semantic_retriever.retrieve(query, top_k=4)
    assert len(hits) >= 1, (
        f"Policy query {query!r} returned [] — threshold may be too high "
        "or semantic embedder misconfigured"
    )
    for hit in hits:
        assert hit.score >= PROD_THRESHOLD, (
            f"Hit {hit.chunk.chunk_id!r} scored {hit.score:.4f} "
            f"but minimum is {PROD_THRESHOLD}"
        )
    # At least one policy or FAQ chunk must appear
    policy_types = {h.chunk.document_type for h in hits}
    assert policy_types & {"policy", "faq"}, (
        f"No policy/faq chunk in top results for {query!r}: {policy_types}"
    )


# =============================================================================
# Test 6 — MRI query rejected end-to-end (semantic, skipped offline)
# =============================================================================


def test_6_mri_query_rejected_end_to_end(
    semantic_retriever: KnowledgeRetriever,
) -> None:
    """End-to-end: 'What is the MRI machine schedule?' must return the
    honest not-found response, never clinic-hours or other unrelated text.

    Uses FastEmbed (skipped if offline) + RuleBasedIntentProvider so the
    full KnowledgeAgent pipeline runs without a Groq API key.
    """
    agent = KnowledgeAgent(NeverCalledProvider(), semantic_retriever)
    response = agent.handle("What is the MRI machine schedule?")
    # The threshold must have filtered everything → fallback, not an answer
    assert response.message == NOT_IN_KNOWLEDGE_BASE_MESSAGE, (
        "MRI query must produce the not-found fallback, not a fabricated answer. "
        "Got: " + repr(response.message)
    )
    assert response.data["citations"] == []


# =============================================================================
# Test 7 — Positive live queries end-to-end (semantic, skipped offline)
# =============================================================================


@pytest.mark.parametrize(
    "query",
    [
        "Who is Dr. Ahmed?",
        "What services does Dr. Ahmed provide?",
        "What is the cancellation policy?",
    ],
)
def test_7_positive_queries_grounded_end_to_end(
    query: str, semantic_retriever: KnowledgeRetriever
) -> None:
    """The three live-test queries from the Phase 8.8.14 spec must produce
    grounded answers (citations present, non-fallback message).

    Uses EchoProvider (not Groq) so it runs without an API key.
    """
    agent = KnowledgeAgent(EchoProvider(), semantic_retriever)
    response = agent.handle(query)

    assert response.message != NOT_IN_KNOWLEDGE_BASE_MESSAGE, (
        f"Query {query!r} must get a grounded answer, not the fallback"
    )
    assert response.message.startswith("grounded:"), (
        f"EchoProvider must have been reached for {query!r}; "
        "got: " + repr(response.message)
    )
    citations = response.data["citations"]
    assert len(citations) >= 1, (
        f"Query {query!r} must produce at least one citation"
    )
    # Every citation score must be above the threshold
    for c in citations:
        assert c["score"] >= PROD_THRESHOLD, (
            f"Citation {c['source']!r} has score {c['score']:.4f} "
            f"below threshold {PROD_THRESHOLD}"
        )


# =============================================================================
# Test 8 — Config exports the correct production threshold
# =============================================================================


def test_8_config_exports_prod_threshold() -> None:
    """Settings.rag_min_similarity must equal 0.45 (the production value)
    selected from measured corpus scores where relevant queries scored
    0.484-0.809 and irrelevant ones scored 0.052-0.439."""
    from app.core.config import Settings

    s = Settings()
    assert s.rag_min_similarity == pytest.approx(0.45), (
        f"Settings.rag_min_similarity should be 0.45, got {s.rag_min_similarity}"
    )


# =============================================================================
# Test 9 — Dependencies wire the threshold into the retriever (offline)
# =============================================================================


def test_9_dependencies_wire_threshold_to_retriever(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_knowledge_retriever() must pass rag_min_similarity to the
    KnowledgeRetriever so the production threshold is active in the
    live application — not just in tests that build it manually.

    Monkeypatches the embedder constructor and KnowledgeRetriever.build
    so no ONNX download is needed.
    """
    import app.api.dependencies as deps
    from app.core.config import get_settings

    captured: dict[str, float] = {}

    original_build = KnowledgeRetriever.build

    def _spy_build(documents, embedder, *, default_top_k=4, default_min_similarity=0.0):
        captured["default_min_similarity"] = default_min_similarity
        return original_build(
            documents,
            embedder,
            default_top_k=default_top_k,
            default_min_similarity=default_min_similarity,
        )

    monkeypatch.setattr(KnowledgeRetriever, "build", staticmethod(_spy_build))
    # Use HashingFallbackEmbedder so no model download is needed
    monkeypatch.setattr(
        deps,
        "get_knowledge_embedder",
        lambda: HashingFallbackEmbedder(dimension=64),
    )
    # Clear cache so our monkeypatched functions are called fresh
    deps.get_knowledge_retriever.cache_clear()

    try:
        retriever = deps.get_knowledge_retriever()
    finally:
        deps.get_knowledge_retriever.cache_clear()

    settings = get_settings()
    assert "default_min_similarity" in captured, (
        "KnowledgeRetriever.build was not called by get_knowledge_retriever"
    )
    assert captured["default_min_similarity"] == pytest.approx(
        settings.rag_min_similarity
    ), (
        f"Dependencies must forward settings.rag_min_similarity "
        f"({settings.rag_min_similarity}) to KnowledgeRetriever.build; "
        f"got {captured['default_min_similarity']}"
    )
    if retriever is not None:
        assert retriever.default_min_similarity == pytest.approx(
            settings.rag_min_similarity
        )
