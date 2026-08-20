"""Phase 9.1 — Entity-Aware RAG Answer Hardening Tests.

Tests the single-doctor entity detection, context restriction,
and reranking mechanisms:

  A. Single-doctor queries:
     - "Who is Dr. Ahmed?" -> DOC-001 only (no cross-doctor noise)
     - "What services does Dr. Ahmed provide?" -> DOC-001 only
     - "What is Dr. Sara's specialization?" -> DOC-002
     - "Tell me about Dr. Bilal Iqbal." -> DOC-003
     - "What is Dr. Hassan's consultation fee?" -> DOC-009
     - "What languages does Dr. Zainab speak?" -> DOC-008

  B. Broad queries:
     - "Which doctors are in the knowledge base?" -> broad FAQ / multiple
     - "Who are the cardiologists?" -> DOC-004 (Dr. Nadia Malik)
     - "What specialties do you have?" -> multiple / general

  C. Mixed entity + policy queries:
     - "What is Dr. Ahmed's cancellation policy?" -> DOC-001 + cancellation policy, no other doctors

  D. Unknown doctor queries:
     - "Who is Dr. Xyz?" -> honest not-found response (no unrelated doctor chunks)
     - "Tell me about Doctor Watson" -> honest not-found response

  E. Complete 12-doctor isolation verification:
     - Verifies every single doctor (DOC-001 through DOC-012) isolates only its own profile.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from app.agents.knowledge_agent import KnowledgeAgent
from app.agents.llm_provider import (
    NOT_IN_KNOWLEDGE_BASE_MESSAGE,
    RuleBasedIntentProvider,
)
from app.rag.chunker import KnowledgeChunk
from app.rag.documents import DocumentLoader
from app.rag.embedder import FastEmbedEmbedder
from app.rag.entity_filter import (
    CLINIC_DOCTORS,
    detect_doctor_entities,
    filter_and_rerank_results,
)
from app.rag.retriever import KnowledgeRetriever
from app.rag.vector_store import VectorSearchResult

REAL_KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "data" / "knowledge"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def fastembed() -> FastEmbedEmbedder:
    embedder = FastEmbedEmbedder()
    try:
        embedder._ensure_model()  # noqa: SLF001
    except Exception as exc:
        pytest.skip(
            f"FastEmbed model unavailable in this environment: {exc!r}. Skipping semantic tests."
        )
    return embedder


@pytest.fixture(scope="module")
def retriever(fastembed: FastEmbedEmbedder) -> KnowledgeRetriever:
    docs = DocumentLoader(REAL_KNOWLEDGE_DIR).load()
    return KnowledgeRetriever.build(docs, fastembed, default_min_similarity=0.45)


@pytest.fixture(scope="module")
def knowledge_agent(retriever: KnowledgeRetriever) -> KnowledgeAgent:
    provider = RuleBasedIntentProvider()
    return KnowledgeAgent(provider, retriever)


def _mk_doctor_hit(doc_id: str, name: str, score: float = 0.8) -> VectorSearchResult:
    chunk = KnowledgeChunk(
        chunk_id=f"doctor:{doc_id}",
        text=f"Doctor: {name}\nDoctor ID: {doc_id}\nSpecialization: Test",
        source="doctors.yaml",
        document_type="doctor",
        document_id=doc_id,
        metadata={"doctor_id": doc_id, "name": name, "chunk_index": 0},
    )
    return VectorSearchResult(chunk=chunk, score=score)


def _mk_policy_hit(section: str, score: float = 0.7) -> VectorSearchResult:
    chunk = KnowledgeChunk(
        chunk_id=f"policy:clinic_policies:{section.lower()}",
        text=f"## {section}\nPolicy body text here.",
        source="clinic_policies.md",
        document_type="policy",
        document_id="clinic_policies",
        metadata={"section_title": section, "chunk_index": 1},
    )
    return VectorSearchResult(chunk=chunk, score=score)


# =============================================================================
# 1. Unit Tests — Entity Detection
# =============================================================================


def test_detect_doctor_by_full_name():
    ids, unknown = detect_doctor_entities("Who is Dr. Ahmed?")
    assert ids == {"DOC-001"}
    assert unknown is False

    ids, unknown = detect_doctor_entities("Tell me about Dr. Bilal Iqbal.")
    assert ids == {"DOC-003"}
    assert unknown is False

    ids, unknown = detect_doctor_entities("What is Dr. Hassan Ali's fee?")
    assert ids == {"DOC-009"}
    assert unknown is False


def test_detect_doctor_by_first_name_and_possessive():
    ids, unknown = detect_doctor_entities("What is Ahmed's specialization?")
    assert ids == {"DOC-001"}
    assert unknown is False

    ids, unknown = detect_doctor_entities("Tell me about Sara.")
    assert ids == {"DOC-002"}
    assert unknown is False

    ids, unknown = detect_doctor_entities("What languages does Zainab speak?")
    assert ids == {"DOC-008"}
    assert unknown is False


def test_detect_doctor_by_id():
    ids, unknown = detect_doctor_entities("What is DOC-001's room?")
    assert ids == {"DOC-001"}
    assert unknown is False

    ids, unknown = detect_doctor_entities("Show info for doc-002")
    assert ids == {"DOC-002"}
    assert unknown is False

    ids, unknown = detect_doctor_entities("Who is DOC-012?")
    assert ids == {"DOC-012"}
    assert unknown is False


def test_detect_broad_queries_yield_no_entities():
    ids, unknown = detect_doctor_entities("Which doctors are in the knowledge base?")
    assert ids == set()
    assert unknown is False

    ids, unknown = detect_doctor_entities("Who are the cardiologists?")
    assert ids == set()
    assert unknown is False

    ids, unknown = detect_doctor_entities("What specialties do you have?")
    assert ids == set()
    assert unknown is False

    ids, unknown = detect_doctor_entities("What are the clinic hours?")
    assert ids == set()
    assert unknown is False


def test_detect_unknown_doctor_entity():
    ids, unknown = detect_doctor_entities("Who is Dr. Xyz?")
    assert ids == set()
    assert unknown is True

    ids, unknown = detect_doctor_entities("Tell me about Doctor Watson.")
    assert ids == set()
    assert unknown is True

    ids, unknown = detect_doctor_entities("What is Dr. Strange's fee?")
    assert ids == set()
    assert unknown is True


def test_general_doctor_phrases_not_flagged_as_unknown():
    # Common noun phrases like "doctor appointment" should not be treated as unknown doctor names
    ids, unknown = detect_doctor_entities("How to book a doctor appointment?")
    assert ids == set()
    assert unknown is False

    ids, unknown = detect_doctor_entities("What are the doctor fees?")
    assert ids == set()
    assert unknown is False


def test_detect_multiple_doctors():
    ids, unknown = detect_doctor_entities("Compare Dr. Ahmed and Dr. Sara")
    assert ids == {"DOC-001", "DOC-002"}
    assert unknown is False


# =============================================================================
# 2. Unit Tests — Filter and Rerank Logic
# =============================================================================


def test_filter_removes_unrelated_doctors_for_single_doctor_query():
    hits = [
        _mk_doctor_hit("DOC-001", "Dr. Ahmed", score=0.8),
        _mk_doctor_hit("DOC-003", "Dr. Bilal Iqbal", score=0.7),
        _mk_doctor_hit("DOC-008", "Dr. Zainab Qureshi", score=0.6),
        _mk_doctor_hit("DOC-011", "Dr. Usman Tariq", score=0.5),
    ]

    filtered = filter_and_rerank_results(hits, "Who is Dr. Ahmed?", top_k=4)

    assert len(filtered) == 1
    assert filtered[0].chunk.chunk_id == "doctor:DOC-001"


def test_filter_preserves_policy_and_prioritizes_target_doctor():
    hits = [
        _mk_policy_hit("Cancellation", score=0.75),
        _mk_doctor_hit("DOC-001", "Dr. Ahmed", score=0.70),
        _mk_doctor_hit("DOC-003", "Dr. Bilal Iqbal", score=0.65),
    ]

    filtered = filter_and_rerank_results(
        hits, "What is Dr. Ahmed's cancellation policy?", top_k=4
    )

    chunk_ids = [h.chunk.chunk_id for h in filtered]
    assert "doctor:DOC-001" in chunk_ids
    assert "policy:clinic_policies:cancellation" in chunk_ids
    assert "doctor:DOC-003" not in chunk_ids  # unrelated doctor removed
    # Target doctor prioritized at index 0
    assert filtered[0].chunk.chunk_id == "doctor:DOC-001"


def test_filter_drops_all_doctors_for_unknown_doctor_query():
    hits = [
        _mk_doctor_hit("DOC-001", "Dr. Ahmed", score=0.6),
        _mk_doctor_hit("DOC-002", "Dr. Sara", score=0.5),
        _mk_policy_hit("General Info", score=0.48),
    ]

    filtered = filter_and_rerank_results(hits, "Who is Dr. Xyz?", top_k=4)

    chunk_ids = [h.chunk.chunk_id for h in filtered]
    assert "doctor:DOC-001" not in chunk_ids
    assert "doctor:DOC-002" not in chunk_ids
    assert "policy:clinic_policies:general info" in chunk_ids


def test_filter_preserves_multiple_doctors_for_broad_query():
    hits = [
        _mk_doctor_hit("DOC-001", "Dr. Ahmed", score=0.8),
        _mk_doctor_hit("DOC-002", "Dr. Sara", score=0.7),
        _mk_doctor_hit("DOC-004", "Dr. Nadia Malik", score=0.6),
    ]

    filtered = filter_and_rerank_results(
        hits, "Which doctors are in the clinic?", top_k=4
    )

    # Broad query leaves all hits intact
    assert len(filtered) == 3
    assert [h.chunk.chunk_id for h in filtered] == [
        "doctor:DOC-001",
        "doctor:DOC-002",
        "doctor:DOC-004",
    ]


# =============================================================================
# 3. Integration Tests — End-to-End Single-Doctor Queries (Group A)
# =============================================================================


def test_e2e_who_is_dr_ahmed(knowledge_agent: KnowledgeAgent):
    response = knowledge_agent.handle("Who is Dr. Ahmed?")

    assert "Dr. Ahmed" in response.message
    assert "DOC-001" in response.message

    # Unrelated doctors must NOT appear in message or citations
    unrelated_doctors = ["Dr. Bilal", "Dr. Hassan", "Dr. Zainab", "Dr. Usman", "DOC-003", "DOC-008", "DOC-009"]
    for doc in unrelated_doctors:
        assert doc not in response.message

    citations = response.data["citations"]
    citation_sources = [c["source"] for c in citations]
    assert "doctor:DOC-001" in citation_sources
    for src in citation_sources:
        assert not (src.startswith("doctor:") and src != "doctor:DOC-001")


def test_e2e_dr_ahmed_services(knowledge_agent: KnowledgeAgent):
    response = knowledge_agent.handle("What services does Dr. Ahmed provide?")

    assert "General Consultation" in response.message or "General Medicine" in response.message
    citations = response.data["citations"]
    citation_sources = [c["source"] for c in citations]
    assert "doctor:DOC-001" in citation_sources
    for src in citation_sources:
        assert not (src.startswith("doctor:") and src != "doctor:DOC-001")


def test_e2e_dr_sara_specialization(knowledge_agent: KnowledgeAgent):
    response = knowledge_agent.handle("What is Dr. Sara's specialization?")

    assert "Dermatology" in response.message
    assert "DOC-002" in response.message
    assert "Doctor ID: DOC-001" not in response.message

    citations = response.data["citations"]
    citation_sources = [c["source"] for c in citations]
    assert "doctor:DOC-002" in citation_sources
    for src in citation_sources:
        assert not (src.startswith("doctor:") and src != "doctor:DOC-002")


def test_e2e_dr_bilal_iqbal(knowledge_agent: KnowledgeAgent):
    response = knowledge_agent.handle("Tell me about Dr. Bilal Iqbal.")

    assert "Dr. Bilal Iqbal" in response.message
    assert "Pediatrics" in response.message
    assert "DOC-003" in response.message

    citations = response.data["citations"]
    citation_sources = [c["source"] for c in citations]
    assert "doctor:DOC-003" in citation_sources
    for src in citation_sources:
        assert not (src.startswith("doctor:") and src != "doctor:DOC-003")


def test_e2e_dr_hassan_fee(knowledge_agent: KnowledgeAgent):
    response = knowledge_agent.handle("What is Dr. Hassan's consultation fee?")

    assert "Dr. Hassan Ali" in response.message or "2000" in response.message
    assert "DOC-009" in response.message

    citations = response.data["citations"]
    citation_sources = [c["source"] for c in citations]
    assert "doctor:DOC-009" in citation_sources
    # Unrelated doctors (e.g. DOC-011, DOC-012) must NOT be present
    for src in citation_sources:
        assert not (src.startswith("doctor:") and src != "doctor:DOC-009")


def test_e2e_dr_zainab_languages(knowledge_agent: KnowledgeAgent):
    response = knowledge_agent.handle("What languages does Dr. Zainab speak?")

    assert "Dr. Zainab Qureshi" in response.message or "Psychiatry" in response.message
    assert "DOC-008" in response.message

    citations = response.data["citations"]
    citation_sources = [c["source"] for c in citations]
    assert "doctor:DOC-008" in citation_sources
    for src in citation_sources:
        assert not (src.startswith("doctor:") and src != "doctor:DOC-008")


# =============================================================================
# 4. Integration Tests — Broad Queries (Group B)
# =============================================================================


def test_e2e_broad_doctors_query(knowledge_agent: KnowledgeAgent):
    response = knowledge_agent.handle("Which doctors are in the knowledge base?")

    assert response.message != NOT_IN_KNOWLEDGE_BASE_MESSAGE
    citations = response.data["citations"]
    assert len(citations) >= 1


def test_e2e_broad_cardiologist_query(knowledge_agent: KnowledgeAgent):
    response = knowledge_agent.handle("Who are the cardiologists?")

    assert "Cardiology" in response.message or "Dr. Nadia Malik" in response.message
    citations = response.data["citations"]
    assert any("DOC-004" in c["source"] for c in citations)


def test_e2e_broad_specialties_query(knowledge_agent: KnowledgeAgent):
    response = knowledge_agent.handle("What specialties does the clinic cover?")

    assert response.message != NOT_IN_KNOWLEDGE_BASE_MESSAGE
    assert len(response.data["citations"]) >= 1


# =============================================================================
# 5. Integration Tests — Mixed Entity + Policy (Group C)
# =============================================================================


def test_e2e_dr_ahmed_cancellation_policy(knowledge_agent: KnowledgeAgent):
    response = knowledge_agent.handle("What is Dr. Ahmed's cancellation policy?")

    assert "Cancellation" in response.message or "Dr. Ahmed" in response.message
    citations = response.data["citations"]
    citation_sources = [c["source"] for c in citations]

    # Must contain Dr. Ahmed and/or cancellation policy
    assert any("DOC-001" in s or "cancellation" in s.lower() or "policy" in s.lower() for s in citation_sources)
    # Unrelated doctors must NOT appear
    for src in citation_sources:
        assert not (src.startswith("doctor:") and src != "doctor:DOC-001")


# =============================================================================
# 6. Integration Tests — Unknown Doctor (Group D)
# =============================================================================


def test_e2e_unknown_doctor_xyz(knowledge_agent: KnowledgeAgent):
    response = knowledge_agent.handle("Who is Dr. Xyz?")

    assert response.message == NOT_IN_KNOWLEDGE_BASE_MESSAGE
    assert response.data["citations"] == []


def test_e2e_unknown_doctor_watson(knowledge_agent: KnowledgeAgent):
    response = knowledge_agent.handle("Tell me about Doctor Watson.")

    assert response.message == NOT_IN_KNOWLEDGE_BASE_MESSAGE
    assert response.data["citations"] == []


# =============================================================================
# 7. Comprehensive 12-Doctor Isolation Verification
# =============================================================================


@pytest.mark.parametrize("doctor", CLINIC_DOCTORS)
def test_e2e_all_twelve_doctors_isolated(
    doctor, knowledge_agent: KnowledgeAgent
):
    query = f"Who is {doctor.name}?"
    response = knowledge_agent.handle(query)

    assert response.message != NOT_IN_KNOWLEDGE_BASE_MESSAGE
    assert doctor.name in response.message or doctor.doctor_id in response.message

    citations = response.data["citations"]
    doctor_citations = [
        c["source"] for c in citations if c["source"].startswith("doctor:")
    ]

    # Only this doctor's chunk may appear among doctor citations
    assert doctor_citations == [f"doctor:{doctor.doctor_id}"], (
        f"Query for {doctor.name} ({doctor.doctor_id}) returned unexpected doctor citations: {doctor_citations}"
    )
