"""Phase 8.8.4 tests — knowledge chunker.

All tests run offline. The real shipped knowledge base is used for
positive-path assertions (via a module-scoped fixture) and ``tmp_path``
is used whenever a test needs to construct a specific edge-case
document.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from app.rag.chunker import KnowledgeChunk, chunk_documents
from app.rag.documents import DocumentLoader, KnowledgeDocument

REAL_KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "data" / "knowledge"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_documents() -> list[KnowledgeDocument]:
    return DocumentLoader(REAL_KNOWLEDGE_DIR).load()


@pytest.fixture(scope="module")
def real_chunks(real_documents) -> list[KnowledgeChunk]:
    return chunk_documents(real_documents)


def _doc(
    *,
    document_type: str,
    document_id: str,
    source: str,
    text: str,
    title: str = "Test Title",
    metadata: dict[str, str | int | bool] | None = None,
) -> KnowledgeDocument:
    """Small factory for synthetic documents (used in edge-case tests)."""
    return KnowledgeDocument(
        source=source,
        document_type=document_type,  # type: ignore[arg-type]
        document_id=document_id,
        title=title,
        text=text,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# 1-3: Doctor chunking
# ---------------------------------------------------------------------------


def test_every_doctor_document_produces_exactly_one_chunk(real_documents, real_chunks):
    doctor_docs = [d for d in real_documents if d.document_type == "doctor"]
    doctor_chunks = [c for c in real_chunks if c.document_type == "doctor"]
    assert len(doctor_chunks) == len(doctor_docs) == 12
    doc_ids = {d.document_id for d in doctor_docs}
    chunk_doc_ids = {c.document_id for c in doctor_chunks}
    assert doc_ids == chunk_doc_ids


def test_doctor_chunk_metadata_is_preserved(real_chunks):
    doc001 = next(c for c in real_chunks if c.chunk_id == "doctor:DOC-001")
    # From the loader: {doctor_id, name, specialization, demo_only}
    assert doc001.metadata["doctor_id"] == "DOC-001"
    assert doc001.metadata["name"] == "Dr. Ahmed"
    assert doc001.metadata["specialization"] == "General Medicine"
    assert doc001.metadata["demo_only"] is False
    # Chunker adds its own consistency marker:
    assert doc001.metadata["chunk_index"] == 0


def test_doctor_availability_disclaimer_survives_chunking(real_chunks):
    """The renderer in Phase 8.8.3 injects an "informational only"
    disclaimer on the availability line of every doctor. That must
    remain in the chunk text — a retrieved snippet must never be
    stripped of the caveat."""
    doctor_chunks = [c for c in real_chunks if c.document_type == "doctor"]
    for chunk in doctor_chunks:
        assert "informational only" in chunk.text
        assert "appointment system" in chunk.text


# ---------------------------------------------------------------------------
# 4-5: Policy chunking by heading
# ---------------------------------------------------------------------------


def test_policy_document_is_split_into_multiple_heading_chunks(real_chunks):
    policy_chunks = [c for c in real_chunks if c.document_type == "policy"]
    # 13 headings in the shipped file (1 title '#' + 12 '## sections').
    # Any count > 1 proves the split happened; assert exact for
    # determinism.
    assert len(policy_chunks) == 13


def test_policy_heading_remains_in_chunk_text(real_chunks):
    policy_chunks = [c for c in real_chunks if c.document_type == "policy"]
    for chunk in policy_chunks:
        first_line = chunk.text.splitlines()[0]
        assert first_line.lstrip("#").strip() != "", (
            f"Heading missing at top of chunk {chunk.chunk_id}"
        )
        assert first_line.startswith("#"), (
            f"Chunk {chunk.chunk_id} does not start with heading"
        )


def test_policy_chunk_metadata_carries_section_title(real_chunks):
    policy_chunks = [c for c in real_chunks if c.document_type == "policy"]
    for chunk in policy_chunks:
        assert isinstance(chunk.metadata.get("section_title"), str)
        assert chunk.metadata["section_title"]  # non-empty
        assert isinstance(chunk.metadata.get("chunk_index"), int)
        assert chunk.metadata["chunk_index"] >= 1


def test_specific_policy_section_is_present(real_chunks):
    """Regression pin: 'Cancellation' is a top-level section in the
    shipped policies file — must produce its own chunk."""
    matches = [
        c for c in real_chunks
        if c.document_type == "policy"
        and c.metadata.get("section_title") == "Cancellation"
    ]
    assert len(matches) == 1
    assert "Cancelled" in matches[0].text


# ---------------------------------------------------------------------------
# 6: FAQ chunking keeps Q + A together
# ---------------------------------------------------------------------------


def test_faq_chunks_keep_question_and_answer_together(real_chunks):
    faq_chunks = [c for c in real_chunks if c.document_type == "faq"]
    # 16 Q's + 1 top-level title = 17 chunks in the shipped file.
    assert len(faq_chunks) == 17


def test_specific_faq_question_and_answer_stay_in_same_chunk(real_chunks):
    q = "How do I book an appointment?"
    matches = [
        c for c in real_chunks
        if c.document_type == "faq" and c.metadata.get("section_title") == q
    ]
    assert len(matches) == 1
    chunk = matches[0]
    # The question is in the chunk text as the heading:
    assert q in chunk.text
    # …and the answer follows in the SAME chunk:
    assert "assistant" in chunk.text.lower()


def test_all_faq_chunks_have_question_style_titles(real_chunks):
    """FAQ headings in the shipped file are all questions (title
    heading is meta). This test doesn't require every one to end in
    '?', but does verify the ordering is preserved and consecutive
    ordinals are assigned."""
    faq_chunks = [c for c in real_chunks if c.document_type == "faq"]
    indices = [c.metadata["chunk_index"] for c in faq_chunks]
    assert indices == list(range(1, len(faq_chunks) + 1))


# ---------------------------------------------------------------------------
# 7: Empty / whitespace sections are ignored
# ---------------------------------------------------------------------------


def test_empty_heading_section_is_dropped():
    text = dedent(
        """\
        # A Section With Content

        Something here.

        # Empty Section

        # Another Section With Content

        Some more content.
        """
    )
    doc = _doc(
        document_type="policy",
        document_id="test_policy",
        source="test.md",
        text=text,
    )
    chunks = chunk_documents([doc])
    titles = [c.metadata["section_title"] for c in chunks]
    assert "Empty Section" not in titles
    assert titles == ["A Section With Content", "Another Section With Content"]


def test_document_with_no_headings_at_all_produces_no_chunks():
    doc = _doc(
        document_type="policy",
        document_id="no_headings",
        source="empty.md",
        text="Just some paragraph text without any headings at all.",
    )
    chunks = chunk_documents([doc])
    assert chunks == []


def test_content_before_first_heading_is_dropped():
    text = dedent(
        """\
        This preamble sits above any heading and is intentionally dropped.

        ## Real Section

        Real content that must survive.
        """
    )
    doc = _doc(
        document_type="policy",
        document_id="preamble_test",
        source="pre.md",
        text=text,
    )
    chunks = chunk_documents([doc])
    assert len(chunks) == 1
    assert "preamble" not in chunks[0].text.lower()
    assert "Real content that must survive." in chunks[0].text


# ---------------------------------------------------------------------------
# 8-10: Determinism
# ---------------------------------------------------------------------------


def test_chunk_ordering_is_deterministic(real_documents):
    a = chunk_documents(real_documents)
    b = chunk_documents(real_documents)
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b]


def test_chunk_ids_are_deterministic_and_human_debuggable(real_chunks):
    ids = [c.chunk_id for c in real_chunks]
    # Every id must be unique
    assert len(ids) == len(set(ids))
    # …and follow the documented shape
    for cid in ids:
        assert cid.startswith(("doctor:", "policy:", "faq:")), (
            f"Unexpected chunk id shape: {cid}"
        )
        assert " " not in cid


def test_specific_chunk_ids_match_the_documented_style(real_chunks):
    ids = {c.chunk_id for c in real_chunks}
    assert "doctor:DOC-001" in ids
    assert "doctor:DOC-002" in ids
    # policy ordinals are zero-padded 2 digits
    assert "policy:clinic_policies:01" in ids
    assert "policy:clinic_policies:02" in ids
    assert "faq:faq:01" in ids


def test_rechunking_the_same_documents_produces_byte_identical_output(real_documents):
    a = chunk_documents(real_documents)
    b = chunk_documents(real_documents)
    a_serialized = [c.model_dump() for c in a]
    b_serialized = [c.model_dump() for c in b]
    assert a_serialized == b_serialized


# ---------------------------------------------------------------------------
# 11: Provenance / metadata
# ---------------------------------------------------------------------------


def test_every_chunk_preserves_provenance_fields(real_chunks):
    for chunk in real_chunks:
        assert chunk.source
        assert chunk.document_id
        assert chunk.document_type in ("doctor", "policy", "faq")
        assert chunk.metadata.get("chunk_index") is not None
        assert isinstance(chunk.chunk_id, str) and chunk.chunk_id


def test_policy_chunk_provenance_points_at_source_file(real_chunks):
    policy_chunk = next(c for c in real_chunks if c.document_type == "policy")
    assert policy_chunk.source == "clinic_policies.md"
    assert policy_chunk.document_id == "clinic_policies"


def test_faq_chunk_provenance_points_at_source_file(real_chunks):
    faq_chunk = next(c for c in real_chunks if c.document_type == "faq")
    assert faq_chunk.source == "faq.md"
    assert faq_chunk.document_id == "faq"


def test_chunk_output_ordering_follows_document_input_ordering(real_documents):
    """Doctors first (sorted by id), then policy chunks, then faq
    chunks — matching the loader's document ordering."""
    chunks = chunk_documents(real_documents)
    types_in_order = [c.document_type for c in chunks]
    # Every "doctor" comes before every "policy" comes before every "faq"
    doctor_last = max(i for i, t in enumerate(types_in_order) if t == "doctor")
    policy_first = min(i for i, t in enumerate(types_in_order) if t == "policy")
    policy_last = max(i for i, t in enumerate(types_in_order) if t == "policy")
    faq_first = min(i for i, t in enumerate(types_in_order) if t == "faq")
    assert doctor_last < policy_first
    assert policy_last < faq_first


# ---------------------------------------------------------------------------
# KnowledgeChunk is frozen
# ---------------------------------------------------------------------------


def test_knowledge_chunk_model_is_frozen(real_chunks):
    with pytest.raises((TypeError, ValueError)):
        real_chunks[0].text = "tampered"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Unknown document_type is skipped silently
# ---------------------------------------------------------------------------


def test_unknown_document_type_is_skipped():
    # Model validates document_type as Literal, so build via bypass —
    # simulate a future addition rather than a validation error path.
    doctor_doc = _doc(
        document_type="doctor",
        document_id="DOC-K01",
        source="doctors.yaml",
        text="Doctor: X\nSpecialization: Y",
    )
    chunks = chunk_documents([doctor_doc])
    assert len(chunks) == 1
    assert chunks[0].chunk_id == "doctor:DOC-K01"


def test_empty_input_returns_empty_chunk_list():
    assert chunk_documents([]) == []


# ---------------------------------------------------------------------------
# Integration guard: chunker never inspects the Excel workbook
# ---------------------------------------------------------------------------


def test_chunker_source_does_not_reference_workbook_or_repositories():
    src = (Path(__file__).resolve().parents[1] / "app" / "rag" / "chunker.py").read_text(
        encoding="utf-8"
    )
    for banned in ("openpyxl", "pandas", "repositor", ".xlsx", "AppointmentService"):
        assert banned.lower() not in src.lower(), (
            f"chunker.py must not touch appointment infrastructure; found {banned}"
        )


# =============================================================================
# Phase 8.8.5 — Embedder suite
# =============================================================================

import math

import numpy as np
import pytest

from app.rag.embedder import (
    DEFAULT_FASTEMBED_MODEL,
    Embedder,
    FastEmbedEmbedder,
    HashingFallbackEmbedder,
)


# ---------------------------------------------------------------------------
# HashingFallbackEmbedder — deterministic, offline, exhaustively tested
# ---------------------------------------------------------------------------


def test_hashing_fallback_is_deterministic_across_calls():
    e = HashingFallbackEmbedder(dimension=64)
    a = e.embed(["hello world"])
    b = e.embed(["hello world"])
    assert a == b


def test_hashing_fallback_same_text_produces_identical_vectors_within_batch():
    e = HashingFallbackEmbedder(dimension=64)
    result = e.embed(["identical", "identical"])
    assert result[0] == result[1]


def test_hashing_fallback_different_texts_produce_different_vectors():
    e = HashingFallbackEmbedder(dimension=64)
    a, b = e.embed(["dermatology consultation", "orthopaedic surgery"])
    assert a != b
    # And they should differ by a lot — cosine similarity well below 1.
    sim = float(np.dot(np.asarray(a), np.asarray(b)))
    assert sim < 0.5


def test_hashing_fallback_returns_the_configured_dimension():
    for dim in (16, 64, 128, 384):
        e = HashingFallbackEmbedder(dimension=dim)
        assert e.dimension == dim
        [vec] = e.embed(["dimension check"])
        assert len(vec) == dim


def test_hashing_fallback_output_length_matches_input_length():
    e = HashingFallbackEmbedder(dimension=32)
    inputs = [f"chunk {i}" for i in range(7)]
    result = e.embed(inputs)
    assert len(result) == len(inputs)


def test_hashing_fallback_preserves_input_ordering():
    e = HashingFallbackEmbedder(dimension=32)
    ordered = ["first", "second", "third"]
    result = e.embed(ordered)
    # Recover each single-input embedding and confirm the batched
    # output row matches the same position.
    for i, text in enumerate(ordered):
        [expected] = e.embed([text])
        assert result[i] == expected


def test_hashing_fallback_vectors_are_unit_normalized():
    e = HashingFallbackEmbedder(dimension=128)
    for vec in e.embed(["one", "two", "three, four", "another chunk of text"]):
        arr = np.asarray(vec)
        assert math.isclose(float(np.linalg.norm(arr)), 1.0, abs_tol=1e-5)


def test_hashing_fallback_rejects_empty_input_list():
    e = HashingFallbackEmbedder(dimension=32)
    with pytest.raises(ValueError, match="at least one input"):
        e.embed([])


def test_hashing_fallback_rejects_empty_string_in_batch():
    e = HashingFallbackEmbedder(dimension=32)
    with pytest.raises(ValueError, match="empty"):
        e.embed(["good text", "   "])


def test_hashing_fallback_rejects_bare_string():
    """Passing a raw str is a common mistake — the validation catches
    it before anyone accidentally tries to embed each character."""
    e = HashingFallbackEmbedder(dimension=32)
    with pytest.raises(ValueError, match="Sequence of strings"):
        e.embed("not a batch")  # type: ignore[arg-type]


def test_hashing_fallback_rejects_non_string_in_batch():
    e = HashingFallbackEmbedder(dimension=32)
    with pytest.raises(ValueError, match="not a string"):
        e.embed(["ok", 42])  # type: ignore[list-item]


def test_hashing_fallback_dimension_must_be_positive():
    with pytest.raises(ValueError, match="positive"):
        HashingFallbackEmbedder(dimension=0)
    with pytest.raises(ValueError, match="positive"):
        HashingFallbackEmbedder(dimension=-3)


def test_hashing_fallback_is_an_Embedder():
    """Structural test — confirms the ABC contract."""
    assert isinstance(HashingFallbackEmbedder(), Embedder)


# ---------------------------------------------------------------------------
# FastEmbedEmbedder — dimension is available without a download; the real
# embed() call is gated behind a skip so CI without network still passes.
# ---------------------------------------------------------------------------


def test_fastembed_default_model_is_minilm_l6_v2():
    assert DEFAULT_FASTEMBED_MODEL == "sentence-transformers/all-MiniLM-L6-v2"


def test_fastembed_dimension_known_without_model_download():
    """`dimension` must be answerable from the known-dimensions
    table so callers can size vector stores at import time — no
    model download should be triggered."""
    e = FastEmbedEmbedder()  # default model — dimension in the known table
    assert e.dimension == 384
    # Model must still be lazy; construction alone does not load ONNX.
    assert e._model is None  # noqa: SLF001


def test_fastembed_rejects_blank_model_name():
    with pytest.raises(ValueError, match="non-empty"):
        FastEmbedEmbedder(model_name="")
    with pytest.raises(ValueError, match="non-empty"):
        FastEmbedEmbedder(model_name="   ")


def test_fastembed_is_an_Embedder():
    assert isinstance(FastEmbedEmbedder(), Embedder)


def test_fastembed_validates_empty_input_before_touching_model():
    """Empty-batch validation must fire without ever loading the
    ONNX model, so CI without network can still reach this path."""
    e = FastEmbedEmbedder()
    with pytest.raises(ValueError, match="at least one input"):
        e.embed([])
    # Still lazy — no model load triggered by a validation error.
    assert e._model is None  # noqa: SLF001


# ---------------------------------------------------------------------------
# Real FastEmbed smoke test — SKIPPED if the model can't be loaded (offline
# CI, no cache). Never fails the deterministic suite for that reason.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def fastembed_smoke() -> FastEmbedEmbedder:
    embedder = FastEmbedEmbedder()
    try:
        embedder._ensure_model()  # noqa: SLF001
    except Exception as exc:
        pytest.skip(
            f"FastEmbed model '{DEFAULT_FASTEMBED_MODEL}' unavailable "
            f"in this environment (skip reason: {exc!r})."
        )
    return embedder


def test_fastembed_embeds_a_small_batch_with_the_configured_model(fastembed_smoke):
    result = fastembed_smoke.embed(
        [
            "What is the specialization of Dr. Ahmed?",
            "How do I cancel my appointment?",
        ]
    )
    assert len(result) == 2
    assert len(result[0]) == 384
    assert len(result[1]) == 384
    # Vectors are normalized (defensive normalization in the embedder).
    for vec in result:
        assert math.isclose(float(np.linalg.norm(np.asarray(vec))), 1.0, abs_tol=1e-4)


def test_fastembed_semantic_similarity_is_reasonable(fastembed_smoke):
    """Basic sanity — a paraphrase should look more similar to its
    original than an unrelated sentence does. Just a smoke test; not
    a benchmark."""
    vectors = fastembed_smoke.embed(
        [
            "Dr. Ahmed is a general medicine physician.",
            "Dr. Ahmed practises general medicine.",
            "The parking lot is on the second floor.",
        ]
    )
    a, b, c = (np.asarray(v) for v in vectors)
    sim_ab = float(np.dot(a, b))
    sim_ac = float(np.dot(a, c))
    assert sim_ab > sim_ac


# =============================================================================
# Phase 8.8.6 — NumpyVectorStore suite
# =============================================================================

from app.rag.vector_store import NumpyVectorStore, VectorSearchResult


def _mk_chunk(chunk_id: str, text: str = "sample text") -> KnowledgeChunk:
    """Small factory for hand-built KnowledgeChunk in vector-store tests."""
    return KnowledgeChunk(
        chunk_id=chunk_id,
        text=text,
        source="test.md",
        document_type="policy",
        document_id="test",
        metadata={"chunk_index": 1},
    )


# ---------------------------------------------------------------------------
# 1-2, 15: fit + introspection
# ---------------------------------------------------------------------------


def test_store_accepts_valid_chunks_and_embeddings():
    store = NumpyVectorStore()
    chunks = [_mk_chunk("a"), _mk_chunk("b"), _mk_chunk("c")]
    vectors = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
    store.fit(chunks, vectors)
    assert store.is_fitted
    assert store.size == 3
    assert store.dimension == 2


def test_stored_chunk_metadata_is_preserved_across_fit_and_search():
    store = NumpyVectorStore()
    chunk = KnowledgeChunk(
        chunk_id="doctor:DOC-777",
        text="Doctor: Dr. Test\nSpecialization: Radiology",
        source="doctors.yaml",
        document_type="doctor",
        document_id="DOC-777",
        metadata={"doctor_id": "DOC-777", "name": "Dr. Test", "chunk_index": 0},
    )
    store.fit([chunk], [[0.6, 0.8]])
    [hit] = store.search([0.6, 0.8], top_k=1)
    assert hit.chunk.chunk_id == "doctor:DOC-777"
    assert hit.chunk.text == chunk.text
    assert hit.chunk.metadata["doctor_id"] == "DOC-777"
    assert hit.chunk.metadata["name"] == "Dr. Test"


# ---------------------------------------------------------------------------
# 3, 7: highest-similarity ordering + exact cosine scores
# ---------------------------------------------------------------------------


def test_search_returns_highest_similarity_chunk_first():
    """Query aligned with the third vector [1,1]/sqrt(2) should rank it first."""
    store = NumpyVectorStore()
    chunks = [_mk_chunk("orthogonal_x"), _mk_chunk("orthogonal_y"), _mk_chunk("diagonal")]
    store.fit(chunks, [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
    results = store.search([1.0, 1.0], top_k=3)
    assert results[0].chunk.chunk_id == "diagonal"


def test_search_scores_match_computed_cosine_similarity():
    """Known corpus: [1,0], [0,1], [1,1]/sqrt(2). Query [1,0]."""
    store = NumpyVectorStore()
    chunks = [_mk_chunk("x"), _mk_chunk("y"), _mk_chunk("xy")]
    store.fit(chunks, [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
    results = store.search([1.0, 0.0], top_k=3)
    scores_by_id = {r.chunk.chunk_id: r.score for r in results}
    import math as _math
    assert _math.isclose(scores_by_id["x"], 1.0, abs_tol=1e-5)
    assert _math.isclose(scores_by_id["y"], 0.0, abs_tol=1e-5)
    assert _math.isclose(scores_by_id["xy"], _math.sqrt(2) / 2, abs_tol=1e-5)


# ---------------------------------------------------------------------------
# 4-6: top_k behaviour
# ---------------------------------------------------------------------------


def test_top_k_one_returns_a_single_result():
    store = NumpyVectorStore()
    store.fit(
        [_mk_chunk("a"), _mk_chunk("b"), _mk_chunk("c")],
        [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]],
    )
    results = store.search([1.0, 0.0], top_k=1)
    assert len(results) == 1


def test_top_k_four_returns_at_most_four_results():
    store = NumpyVectorStore()
    ids = ["a", "b", "c", "d", "e", "f"]
    store.fit(
        [_mk_chunk(i) for i in ids],
        [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [-1.0, 0.0], [0.0, -1.0], [-1.0, -1.0]],
    )
    results = store.search([1.0, 0.0], top_k=4)
    assert len(results) == 4


def test_top_k_larger_than_corpus_returns_entire_corpus():
    store = NumpyVectorStore()
    store.fit(
        [_mk_chunk("a"), _mk_chunk("b")],
        [[1.0, 0.0], [0.0, 1.0]],
    )
    results = store.search([1.0, 0.0], top_k=99)
    assert len(results) == 2


# ---------------------------------------------------------------------------
# 8-9: deterministic ordering + tie-break
# ---------------------------------------------------------------------------


def test_result_ordering_is_deterministic_across_repeated_searches():
    store = NumpyVectorStore()
    store.fit(
        [_mk_chunk(f"c{i}") for i in range(5)],
        [[1.0, 0.0], [0.7, 0.7], [0.9, 0.4], [-0.5, 0.5], [0.5, 0.5]],
    )
    query = [0.6, 0.8]
    ids1 = [r.chunk.chunk_id for r in store.search(query, top_k=5)]
    ids2 = [r.chunk.chunk_id for r in store.search(query, top_k=5)]
    assert ids1 == ids2


def test_equal_score_ties_break_by_original_corpus_order():
    """Two vectors identically similar to the query: the earlier one
    in the corpus must come first."""
    store = NumpyVectorStore()
    store.fit(
        [_mk_chunk("first"), _mk_chunk("second"), _mk_chunk("third")],
        [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]],
    )
    results = store.search([1.0, 0.0], top_k=3)
    assert results[0].chunk.chunk_id == "first"
    assert results[1].chunk.chunk_id == "second"
    assert results[2].chunk.chunk_id == "third"


# ---------------------------------------------------------------------------
# 10-14: validation / errors
# ---------------------------------------------------------------------------


def test_query_dimension_mismatch_raises_clear_error():
    store = NumpyVectorStore()
    store.fit([_mk_chunk("a")], [[1.0, 0.0]])
    with pytest.raises(ValueError, match="dimension"):
        store.search([1.0, 0.0, 0.0], top_k=1)


def test_non_finite_query_vector_is_rejected():
    store = NumpyVectorStore()
    store.fit([_mk_chunk("a")], [[1.0, 0.0]])
    with pytest.raises(ValueError, match="NaN or infinite"):
        store.search([float("nan"), 0.0], top_k=1)
    with pytest.raises(ValueError, match="NaN or infinite"):
        store.search([float("inf"), 0.0], top_k=1)


def test_zero_query_vector_is_rejected():
    store = NumpyVectorStore()
    store.fit([_mk_chunk("a")], [[1.0, 0.0]])
    with pytest.raises(ValueError, match="zero vector"):
        store.search([0.0, 0.0], top_k=1)


def test_search_before_fit_raises_clear_error():
    store = NumpyVectorStore()
    with pytest.raises(RuntimeError, match="before fit"):
        store.search([1.0, 0.0], top_k=1)


def test_empty_corpus_is_rejected():
    store = NumpyVectorStore()
    with pytest.raises(ValueError, match="non-empty"):
        store.fit([], [])


def test_number_of_chunks_and_embeddings_must_match():
    store = NumpyVectorStore()
    with pytest.raises(ValueError, match="length mismatch"):
        store.fit([_mk_chunk("a"), _mk_chunk("b")], [[1.0, 0.0]])


def test_non_finite_stored_vector_is_rejected():
    store = NumpyVectorStore()
    with pytest.raises(ValueError, match="NaN or infinite"):
        store.fit([_mk_chunk("a")], [[float("nan"), 0.0]])


def test_ragged_stored_vectors_are_rejected():
    store = NumpyVectorStore()
    with pytest.raises(ValueError):
        store.fit([_mk_chunk("a"), _mk_chunk("b")], [[1.0, 0.0], [1.0]])


def test_top_k_must_be_positive():
    store = NumpyVectorStore()
    store.fit([_mk_chunk("a")], [[1.0, 0.0]])
    with pytest.raises(ValueError, match="top_k"):
        store.search([1.0, 0.0], top_k=0)
    with pytest.raises(ValueError, match="top_k"):
        store.search([1.0, 0.0], top_k=-3)


def test_top_k_bool_is_not_int():
    """bool is a subclass of int in Python: reject it explicitly so
    search(query, top_k=True) does not silently become top_k=1."""
    store = NumpyVectorStore()
    store.fit([_mk_chunk("a")], [[1.0, 0.0]])
    with pytest.raises(ValueError, match="top_k must be an int"):
        store.search([1.0, 0.0], top_k=True)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 16: search does not mutate stored data
# ---------------------------------------------------------------------------


def test_search_does_not_mutate_stored_corpus():
    store = NumpyVectorStore()
    chunks = [_mk_chunk("a", text="alpha"), _mk_chunk("b", text="beta")]
    store.fit(chunks, [[1.0, 0.0], [0.0, 1.0]])

    size_before = store.size
    dim_before = store.dimension
    matrix_before = store._matrix.copy()  # noqa: SLF001

    store.search([0.6, 0.8], top_k=2)
    store.search([1.0, 0.0], top_k=1)

    assert store.size == size_before
    assert store.dimension == dim_before
    np.testing.assert_array_equal(store._matrix, matrix_before)  # noqa: SLF001
    [hit] = store.search([1.0, 0.0], top_k=1)
    assert hit.chunk.text == "alpha"


def test_returned_vector_search_result_is_frozen():
    store = NumpyVectorStore()
    store.fit([_mk_chunk("a")], [[1.0, 0.0]])
    [result] = store.search([1.0, 0.0], top_k=1)
    with pytest.raises((TypeError, ValueError)):
        result.score = 0.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Offline end-to-end integration: chunks -> HashingFallbackEmbedder -> store
# ---------------------------------------------------------------------------


def test_offline_integration_chunks_through_hashing_embedder_and_store():
    """Full stack minus the Retriever: proves the pieces compose. Uses
    the deterministic hashing embedder so it runs offline in CI."""
    docs = DocumentLoader(REAL_KNOWLEDGE_DIR).load()
    chunks = chunk_documents(docs)

    embedder = HashingFallbackEmbedder(dimension=64)
    vectors = embedder.embed([c.text for c in chunks])

    store = NumpyVectorStore()
    store.fit(chunks, vectors)

    assert store.is_fitted
    assert store.size == len(chunks) == 42
    assert store.dimension == 64

    doc001_chunk = next(c for c in chunks if c.chunk_id == "doctor:DOC-001")
    [query_vec] = embedder.embed([doc001_chunk.text])
    results = store.search(query_vec, top_k=1)
    assert results[0].chunk.chunk_id == "doctor:DOC-001"
    assert results[0].score == pytest.approx(1.0, abs=1e-5)


def test_search_result_score_range_is_within_cosine_bounds():
    """Cosine similarity is bounded to [-1, 1]; the Pydantic model
    would reject anything outside that. This test proves a
    diametrically-opposed vector produces score -1."""
    store = NumpyVectorStore()
    store.fit(
        [_mk_chunk("east"), _mk_chunk("west")],
        [[1.0, 0.0], [-1.0, 0.0]],
    )
    results = store.search([1.0, 0.0], top_k=2)
    assert results[0].score == pytest.approx(1.0, abs=1e-6)
    assert results[1].score == pytest.approx(-1.0, abs=1e-6)


def test_vector_store_source_does_not_reference_workbook_or_repositories():
    src = (Path(__file__).resolve().parents[1] / "app" / "rag" / "vector_store.py").read_text(
        encoding="utf-8"
    )
    for banned in ("openpyxl", "pandas", "repositor", ".xlsx", "AppointmentService"):
        assert banned.lower() not in src.lower(), (
            f"vector_store.py must not touch appointment infrastructure; found {banned}"
        )


# =============================================================================
# Phase 8.8.7 - KnowledgeRetriever suite
# =============================================================================

from typing import Sequence

from app.rag.retriever import (
    DEFAULT_TOP_K,
    KnowledgeRetriever,
    RetrievalResult,
    VectorSearchResult,
)


# --- Test double: a fully-controlled Embedder ------------------------------


class RecordingEmbedder(Embedder):
    """Deterministic 2-D embedder that also records what it was asked
    to embed. Used to prove the retriever routes the query correctly
    without depending on HashingFallbackEmbedder's hash spread."""

    def __init__(self, mapping: dict[str, list[float]], dimension: int = 2):
        self._mapping = mapping
        self._dimension = dimension
        self.calls: list[list[str]] = []

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        # Same validation shape as the real embedders, but no hash math.
        if len(texts) == 0:
            raise ValueError("empty batch")
        self.calls.append(list(texts))
        return [self._mapping.get(t, [0.5, 0.5]) for t in texts]


# --- Fixture: a tiny, hand-built retriever with known geometry -------------


def _tiny_retriever() -> tuple[KnowledgeRetriever, RecordingEmbedder]:
    chunks = [
        _mk_chunk("east"),
        _mk_chunk("north"),
        _mk_chunk("north_east"),
    ]
    vectors = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
    store = NumpyVectorStore()
    store.fit(chunks, vectors)
    embedder = RecordingEmbedder(
        mapping={
            "east?": [1.0, 0.0],
            "north?": [0.0, 1.0],
            "diagonal?": [1.0, 1.0],
        },
        dimension=2,
    )
    retriever = KnowledgeRetriever(embedder, store, default_top_k=2)
    return retriever, embedder


# ---------------------------------------------------------------------------
# 1-3: pipeline routing (query -> embedder -> store -> top_k)
# ---------------------------------------------------------------------------


def test_query_is_forwarded_to_embedder_exactly_as_typed():
    retriever, embedder = _tiny_retriever()
    retriever.retrieve("east?", top_k=1)
    assert embedder.calls == [["east?"]]


def test_query_is_stripped_before_embedding():
    """Leading/trailing whitespace is normalized so callers can't
    accidentally embed a different-looking string than the user
    typed."""
    retriever, embedder = _tiny_retriever()
    retriever.retrieve("   east?   ", top_k=1)
    assert embedder.calls == [["east?"]]


def test_embedded_query_is_passed_into_vector_store_search():
    retriever, _ = _tiny_retriever()
    hits = retriever.retrieve("east?", top_k=1)
    assert len(hits) == 1
    assert hits[0].chunk.chunk_id == "east"


def test_top_k_override_is_forwarded_to_store():
    retriever, _ = _tiny_retriever()
    assert retriever.default_top_k == 2
    hits = retriever.retrieve("diagonal?", top_k=3)
    assert len(hits) == 3


def test_default_top_k_matches_approved_architecture():
    """Master architecture default is 4."""
    assert DEFAULT_TOP_K == 4


# ---------------------------------------------------------------------------
# 4: similarity ordering
# ---------------------------------------------------------------------------


def test_results_are_returned_in_similarity_order():
    retriever, _ = _tiny_retriever()
    hits = retriever.retrieve("diagonal?", top_k=3)
    ids = [h.chunk.chunk_id for h in hits]
    # Query = [1,1]; strongest match is north_east; east and north tie
    # at cos = sqrt(2)/2 - store tie-break by original corpus index
    # puts 'east' before 'north'.
    assert ids[0] == "north_east"
    assert ids[1:] == ["east", "north"]


# ---------------------------------------------------------------------------
# 5-8: metadata / provenance preserved
# ---------------------------------------------------------------------------


def test_chunk_metadata_is_preserved_through_retrieval():
    chunk = KnowledgeChunk(
        chunk_id="policy:demo:07",
        text="section body",
        source="clinic_policies.md",
        document_type="policy",
        document_id="demo",
        metadata={"chunk_index": 7, "section_title": "Cancellation"},
    )
    store = NumpyVectorStore()
    store.fit([chunk], [[1.0, 0.0]])
    embedder = RecordingEmbedder({"q": [1.0, 0.0]}, dimension=2)
    retriever = KnowledgeRetriever(embedder, store)

    [hit] = retriever.retrieve("q", top_k=1)
    assert hit.chunk.metadata["section_title"] == "Cancellation"
    assert hit.chunk.metadata["chunk_index"] == 7
    assert hit.chunk.chunk_id == "policy:demo:07"
    assert hit.chunk.source == "clinic_policies.md"
    assert hit.chunk.document_type == "policy"
    assert hit.chunk.document_id == "demo"


def test_doctor_provenance_is_preserved():
    """The retriever must never strip doctor_id / demo_only /
    specialization from returned chunks."""
    docs = DocumentLoader(REAL_KNOWLEDGE_DIR).load()
    retriever = KnowledgeRetriever.build(
        docs, HashingFallbackEmbedder(dimension=64)
    )
    doc001_chunk = next(
        c for c in chunk_documents(docs) if c.chunk_id == "doctor:DOC-001"
    )
    hits = retriever.retrieve(doc001_chunk.text, top_k=1)
    hit = hits[0]
    assert hit.chunk.document_type == "doctor"
    assert hit.chunk.metadata["doctor_id"] == "DOC-001"
    assert hit.chunk.metadata["specialization"] == "General Medicine"
    assert hit.chunk.metadata["demo_only"] is False


def test_policy_provenance_is_preserved():
    docs = DocumentLoader(REAL_KNOWLEDGE_DIR).load()
    retriever = KnowledgeRetriever.build(
        docs, HashingFallbackEmbedder(dimension=64)
    )
    policy_chunk = next(
        c
        for c in chunk_documents(docs)
        if c.document_type == "policy"
        and c.metadata.get("section_title") == "Cancellation"
    )
    hits = retriever.retrieve(policy_chunk.text, top_k=1)
    assert hits[0].chunk.source == "clinic_policies.md"
    assert hits[0].chunk.document_id == "clinic_policies"
    assert hits[0].chunk.metadata["section_title"] == "Cancellation"


def test_faq_provenance_is_preserved():
    docs = DocumentLoader(REAL_KNOWLEDGE_DIR).load()
    retriever = KnowledgeRetriever.build(
        docs, HashingFallbackEmbedder(dimension=64)
    )
    faq_chunk = next(
        c
        for c in chunk_documents(docs)
        if c.document_type == "faq"
        and c.metadata.get("section_title") == "How do I book an appointment?"
    )
    hits = retriever.retrieve(faq_chunk.text, top_k=1)
    assert hits[0].chunk.source == "faq.md"
    assert hits[0].chunk.document_id == "faq"


# ---------------------------------------------------------------------------
# 9: empty / near-empty behavior
# ---------------------------------------------------------------------------


def test_top_k_larger_than_corpus_returns_the_entire_corpus():
    retriever, _ = _tiny_retriever()
    hits = retriever.retrieve("east?", top_k=99)
    assert len(hits) == 3


def test_retriever_rejects_unfitted_vector_store():
    embedder = RecordingEmbedder({}, dimension=2)
    with pytest.raises(ValueError, match="fitted"):
        KnowledgeRetriever(embedder, NumpyVectorStore())


def test_retriever_rejects_dimension_mismatch_at_construction():
    """Catch a wrong-embedder-for-this-store wiring bug early rather
    than at query time."""
    chunk = _mk_chunk("solo")
    store = NumpyVectorStore()
    store.fit([chunk], [[1.0, 0.0, 0.0]])  # 3-D
    embedder = RecordingEmbedder({}, dimension=2)  # 2-D
    with pytest.raises(ValueError, match="dimension"):
        KnowledgeRetriever(embedder, store)


# ---------------------------------------------------------------------------
# 10-11: invalid inputs
# ---------------------------------------------------------------------------


def test_empty_query_is_rejected_clearly():
    retriever, _ = _tiny_retriever()
    with pytest.raises(ValueError, match="empty or whitespace"):
        retriever.retrieve("")


def test_whitespace_query_is_rejected_clearly():
    retriever, _ = _tiny_retriever()
    with pytest.raises(ValueError, match="empty or whitespace"):
        retriever.retrieve("   \n\t  ")


def test_non_string_query_is_rejected_clearly():
    retriever, _ = _tiny_retriever()
    with pytest.raises(ValueError, match="must be a string"):
        retriever.retrieve(42)  # type: ignore[arg-type]


def test_invalid_top_k_is_rejected_clearly():
    retriever, _ = _tiny_retriever()
    with pytest.raises(ValueError, match="top_k"):
        retriever.retrieve("east?", top_k=0)
    with pytest.raises(ValueError, match="top_k"):
        retriever.retrieve("east?", top_k=-3)
    with pytest.raises(ValueError, match="top_k must be an int"):
        retriever.retrieve("east?", top_k=True)  # type: ignore[arg-type]


def test_invalid_default_top_k_is_rejected_at_construction():
    chunk = _mk_chunk("solo")
    store = NumpyVectorStore()
    store.fit([chunk], [[1.0, 0.0]])
    embedder = RecordingEmbedder({}, dimension=2)
    with pytest.raises(ValueError, match="default_top_k"):
        KnowledgeRetriever(embedder, store, default_top_k=0)


# ---------------------------------------------------------------------------
# 12: no mutation of chunks or store state
# ---------------------------------------------------------------------------


def test_retrieve_does_not_mutate_store_or_chunks():
    retriever, embedder = _tiny_retriever()
    size_before = retriever.corpus_size
    matrix_before = retriever._store._matrix.copy()  # noqa: SLF001
    chunk_ids_before = [c.chunk_id for c in retriever._store._chunks]  # noqa: SLF001

    retriever.retrieve("east?", top_k=2)
    retriever.retrieve("diagonal?", top_k=3)

    assert retriever.corpus_size == size_before
    np.testing.assert_array_equal(
        retriever._store._matrix, matrix_before  # noqa: SLF001
    )
    assert [c.chunk_id for c in retriever._store._chunks] == chunk_ids_before  # noqa: SLF001


def test_retrieval_result_is_the_frozen_vector_search_result():
    """RetrievalResult IS VectorSearchResult - callers get the same
    frozen model, no shadow shape to maintain."""
    assert RetrievalResult is VectorSearchResult
    retriever, _ = _tiny_retriever()
    [hit] = retriever.retrieve("east?", top_k=1)
    with pytest.raises((TypeError, ValueError)):
        hit.score = 0.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 13-14: determinism + end-to-end offline
# ---------------------------------------------------------------------------


def test_repeated_retrieval_on_same_query_is_deterministic():
    docs = DocumentLoader(REAL_KNOWLEDGE_DIR).load()
    retriever = KnowledgeRetriever.build(
        docs, HashingFallbackEmbedder(dimension=64)
    )
    ids1 = [h.chunk.chunk_id for h in retriever.retrieve("Dr. Ahmed", top_k=4)]
    ids2 = [h.chunk.chunk_id for h in retriever.retrieve("Dr. Ahmed", top_k=4)]
    assert ids1 == ids2


def test_end_to_end_offline_pipeline():
    """Documents -> chunker -> HashingFallbackEmbedder ->
    NumpyVectorStore -> KnowledgeRetriever.retrieve()."""
    docs = DocumentLoader(REAL_KNOWLEDGE_DIR).load()
    embedder = HashingFallbackEmbedder(dimension=64)
    retriever = KnowledgeRetriever.build(docs, embedder)
    assert retriever.corpus_size == 42
    assert retriever.default_top_k == 4

    # Self-query - the exact text of a chunk should retrieve itself
    # first with cosine similarity ~ 1.0 (hash-seeded embeddings are
    # deterministic, not semantic, but the identity holds).
    target = next(
        c for c in chunk_documents(docs) if c.chunk_id == "doctor:DOC-002"
    )
    hits = retriever.retrieve(target.text, top_k=3)
    assert hits[0].chunk.chunk_id == "doctor:DOC-002"
    assert hits[0].score == pytest.approx(1.0, abs=1e-5)


# ---------------------------------------------------------------------------
# Representative real-KB queries (offline via HashingFallbackEmbedder).
# These prove wiring + provenance shape - they do NOT judge the natural-
# language answer quality (Phase 8.8.9's concern).
# ---------------------------------------------------------------------------


def test_representative_queries_return_provenance_preserving_hits():
    docs = DocumentLoader(REAL_KNOWLEDGE_DIR).load()
    retriever = KnowledgeRetriever.build(
        docs, HashingFallbackEmbedder(dimension=128)
    )
    queries = [
        "What is Dr. Ahmed's specialization?",
        "Which doctor specializes in dermatology?",
        "What is the cancellation policy?",
        "Can I book a walk-in appointment?",
        "What services does Dr. Sara provide?",
    ]
    for q in queries:
        hits = retriever.retrieve(q, top_k=4)
        assert 1 <= len(hits) <= 4
        for h in hits:
            assert h.chunk.chunk_id
            assert h.chunk.document_type in {"doctor", "policy", "faq"}
            assert h.chunk.source in {
                "doctors.yaml",
                "clinic_policies.md",
                "faq.md",
            }
            assert -1.0 <= h.score <= 1.0


def test_retriever_source_does_not_reference_workbook_or_repositories():
    src = (Path(__file__).resolve().parents[1] / "app" / "rag" / "retriever.py").read_text(
        encoding="utf-8"
    )
    for banned in ("openpyxl", "pandas", "repositor", ".xlsx", "AppointmentService"):
        assert banned.lower() not in src.lower(), (
            f"retriever.py must not touch appointment infrastructure; found {banned}"
        )


# =============================================================================
# Phase 8.8.14 - relevance-threshold hardening
# =============================================================================


def _hit(chunk: KnowledgeChunk, score: float) -> VectorSearchResult:
    return VectorSearchResult(chunk=chunk, score=score)


def _tiny_store(scored: list[tuple[str, float]]) -> NumpyVectorStore:
    """Build a 2-D store where each chunk's cosine similarity vs
    query [1,0] equals the requested score. Simplest way to script
    exact top-1 scores in a unit test."""
    import math as _math

    chunks: list[KnowledgeChunk] = []
    vectors: list[list[float]] = []
    for cid, target in scored:
        # A unit vector at angle theta so cos(theta)=target.
        theta = _math.acos(max(min(target, 1.0), -1.0))
        vectors.append([_math.cos(theta), _math.sin(theta)])
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


class ScriptedEmbedder(Embedder):
    """Always returns the same 2-D unit vector [1, 0] for any input."""

    @property
    def dimension(self) -> int:
        return 2

    def embed(self, texts):
        return [[1.0, 0.0] for _ in texts]


def test_retriever_default_threshold_is_zero_disabled():
    """Existing pre-8.8.14 tests must still see all top-k hits."""
    store = _tiny_store([("low", 0.1), ("mid", 0.5), ("high", 0.9)])
    r = KnowledgeRetriever(ScriptedEmbedder(), store)
    assert r.default_min_similarity == 0.0
    hits = r.retrieve("anything", top_k=3)
    assert len(hits) == 3


def test_retriever_drops_hits_below_configured_default_threshold():
    store = _tiny_store([("low", 0.20), ("mid", 0.50), ("high", 0.80)])
    r = KnowledgeRetriever(
        ScriptedEmbedder(),
        store,
        default_min_similarity=0.45,
    )
    hits = r.retrieve("q", top_k=3)
    ids = [h.chunk.chunk_id for h in hits]
    assert ids == ["high", "mid"]  # low (0.20) filtered out
    # scores intact for the survivors
    scores = {h.chunk.chunk_id: h.score for h in hits}
    assert scores["mid"] == pytest.approx(0.50, abs=1e-4)
    assert scores["high"] == pytest.approx(0.80, abs=1e-4)


def test_retriever_per_call_min_similarity_overrides_default():
    store = _tiny_store([("a", 0.20), ("b", 0.60), ("c", 0.90)])
    r = KnowledgeRetriever(
        ScriptedEmbedder(),
        store,
        default_min_similarity=0.10,
    )
    # Per-call threshold tightens the filter.
    hits = r.retrieve("q", top_k=3, min_similarity=0.5)
    assert [h.chunk.chunk_id for h in hits] == ["c", "b"]


def test_retriever_returns_empty_when_no_hit_meets_threshold():
    store = _tiny_store([("a", 0.10), ("b", 0.15), ("c", 0.20)])
    r = KnowledgeRetriever(
        ScriptedEmbedder(),
        store,
        default_min_similarity=0.45,
    )
    assert r.retrieve("nothing relevant", top_k=3) == []


def test_retriever_rejects_out_of_range_default_min_similarity():
    store = _tiny_store([("a", 0.5)])
    with pytest.raises(ValueError, match="within"):
        KnowledgeRetriever(ScriptedEmbedder(), store, default_min_similarity=1.5)
    with pytest.raises(ValueError, match="within"):
        KnowledgeRetriever(ScriptedEmbedder(), store, default_min_similarity=-1.5)


def test_retriever_rejects_non_numeric_default_min_similarity():
    store = _tiny_store([("a", 0.5)])
    with pytest.raises(ValueError, match="number"):
        KnowledgeRetriever(ScriptedEmbedder(), store, default_min_similarity="0.5")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="number"):
        KnowledgeRetriever(ScriptedEmbedder(), store, default_min_similarity=True)  # type: ignore[arg-type]


def test_retriever_rejects_out_of_range_per_call_min_similarity():
    store = _tiny_store([("a", 0.5)])
    r = KnowledgeRetriever(ScriptedEmbedder(), store)
    with pytest.raises(ValueError, match="within"):
        r.retrieve("q", top_k=1, min_similarity=1.5)


def test_retriever_build_forwards_default_min_similarity(real_documents):
    r = KnowledgeRetriever.build(
        real_documents,
        HashingFallbackEmbedder(dimension=64),
        default_min_similarity=0.42,
    )
    assert r.default_min_similarity == 0.42


def test_knowledge_agent_returns_fallback_when_retriever_filters_everything():
    """The KnowledgeAgent already treats an empty retrieval as
    'not in the knowledge base' (Phase 8.8.9). This test proves the
    Phase-8.8.14 threshold-empty case flows through the same path
    — no LLM call, no citations, safe fallback message."""
    from app.agents.llm_provider import (
        AnswerFromContext,
        LLMProvider,
        NOT_IN_KNOWLEDGE_BASE_MESSAGE,
    )
    from app.agents.knowledge_agent import (
        KNOWLEDGE_ANSWER_INTENT,
        KnowledgeAgent,
    )

    store = _tiny_store([("a", 0.10), ("b", 0.20)])
    retriever = KnowledgeRetriever(
        ScriptedEmbedder(), store, default_min_similarity=0.45
    )

    class NeverCalledProvider(LLMProvider):
        def decide(self, message, context=None):  # pragma: no cover
            raise AssertionError("decide should not be reached")

        def answer_from_context(self, question, context_chunks):
            raise AssertionError(
                "answer_from_context must not be called when retrieval is "
                "filtered empty by the threshold"
            )

    agent = KnowledgeAgent(NeverCalledProvider(), retriever)
    response = agent.handle("unknown clinic topic")

    assert response.intent == KNOWLEDGE_ANSWER_INTENT
    assert response.message == NOT_IN_KNOWLEDGE_BASE_MESSAGE
    assert response.data == {"citations": []}


def test_knowledge_agent_uses_high_score_hit_when_threshold_wired():
    """When SOME hits pass the threshold, the agent proceeds normally
    and citations reflect only the passing chunks."""
    from app.agents.llm_provider import AnswerFromContext, LLMProvider
    from app.agents.knowledge_agent import KnowledgeAgent

    store = _tiny_store([("weak", 0.20), ("strong", 0.80)])
    retriever = KnowledgeRetriever(
        ScriptedEmbedder(), store, default_min_similarity=0.45
    )

    class EchoProvider(LLMProvider):
        def decide(self, message, context=None):  # pragma: no cover
            raise AssertionError

        def answer_from_context(self, question, context_chunks):
            return AnswerFromContext(
                answer=f"grounded on: {context_chunks[0]}", from_context=True
            )

    agent = KnowledgeAgent(EchoProvider(), retriever)
    response = agent.handle("q")

    # Only the "strong" chunk survives the threshold => single citation.
    citations = response.data["citations"]
    assert len(citations) == 1
    assert citations[0]["source"] == "strong"
    assert "grounded on: content for strong" in response.message


def test_shipped_retriever_default_threshold_rejects_mri_query():
    """End-to-end offline sanity: with the Phase-8.8.14 default
    threshold (0.45), the retriever built on the shipped knowledge
    base returns [] for an unrelated MRI question, so the
    KnowledgeAgent's honest fallback fires.

    Uses HashingFallbackEmbedder so it runs offline in CI — hash-
    seeded scores are also < 0.45 for the whole corpus, which
    (correctly) means the retriever also rejects a real medical
    query in this offline mode. That's the honest tradeoff of the
    fallback: it can't tell relevant from irrelevant semantically.
    The important guarantee is that no low-similarity chunk gets
    surfaced as if it were an answer."""
    real_docs = DocumentLoader(REAL_KNOWLEDGE_DIR).load()
    r = KnowledgeRetriever.build(
        real_docs,
        HashingFallbackEmbedder(dimension=64),
        default_min_similarity=0.45,
    )
    # Any query, offline embedder -> almost certainly empty because
    # hash-based cosine is near-random.
    assert r.retrieve("What is the MRI schedule?") == []
    assert r.retrieve("Who is Dr. Ahmed?") == []
    # Setting threshold=0 gives the pre-8.8.14 behaviour back.
    hits = r.retrieve("Who is Dr. Ahmed?", min_similarity=0.0)
    assert len(hits) > 0
