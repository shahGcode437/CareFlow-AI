"""Phase 8.8.3 tests — DocumentLoader + Pydantic validation.

All tests run offline and do not require the fastembed model. Tests
that need mutation build a synthetic knowledge directory under
``tmp_path``; the real shipped knowledge base under
``backend/data/knowledge`` is never modified.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
import yaml

from app.rag.documents import (
    DoctorKnowledge,
    DocumentLoader,
    KnowledgeDocument,
    KnowledgeLoadError,
    render_doctor,
)

REAL_KNOWLEDGE_DIR = Path(__file__).resolve().parents[1] / "data" / "knowledge"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def real_documents() -> list[KnowledgeDocument]:
    """Loaded once for read-only assertions against the shipped
    knowledge base."""
    return DocumentLoader(REAL_KNOWLEDGE_DIR).load()


def _write_minimal_kb(base: Path, doctors_yaml: str | None = None) -> Path:
    """Write a minimal-but-valid knowledge base under ``base`` and
    return that path. `doctors_yaml` overrides the doctors file when
    a test needs a specific bad shape."""
    base.mkdir(parents=True, exist_ok=True)
    if doctors_yaml is None:
        doctors_yaml = dedent(
            """\
            doctors:
              - doctor_id: DOC-X01
                name: Dr. Test One
                specialization: General Medicine
                qualifications: [MBBS]
                experience_years: 5
                services: [General Consultation]
                consultation_fee_pkr: 1500
                available_days_summary: "Monday 10:00 AM - 1:00 PM"
                clinic_room: "Room 1"
                languages: [Urdu, English]
                bio: "Test doctor one."
                demo_only: true
            """
        )
    (base / "doctors.yaml").write_text(doctors_yaml, encoding="utf-8")
    (base / "clinic_policies.md").write_text(
        "# Test Policy\n\nSome policy text.\n", encoding="utf-8"
    )
    (base / "faq.md").write_text("# FAQ\n\nSome faq text.\n", encoding="utf-8")
    return base


# ---------------------------------------------------------------------------
# 1-6: shipped knowledge base loads and validates
# ---------------------------------------------------------------------------


def test_shipped_doctors_yaml_loads_successfully(real_documents):
    doctor_docs = [d for d in real_documents if d.document_type == "doctor"]
    assert len(doctor_docs) > 0


def test_exactly_twelve_doctors_are_loaded(real_documents):
    doctor_docs = [d for d in real_documents if d.document_type == "doctor"]
    assert len(doctor_docs) == 12


def test_doctor_ids_are_unique_in_shipped_kb(real_documents):
    ids = [
        d.metadata["doctor_id"]
        for d in real_documents
        if d.document_type == "doctor"
    ]
    assert len(ids) == len(set(ids))


def test_shipped_kb_contains_doc_001(real_documents):
    ids = {
        d.metadata["doctor_id"]
        for d in real_documents
        if d.document_type == "doctor"
    }
    assert "DOC-001" in ids


def test_shipped_kb_contains_doc_002(real_documents):
    ids = {
        d.metadata["doctor_id"]
        for d in real_documents
        if d.document_type == "doctor"
    }
    assert "DOC-002" in ids


def test_all_required_doctor_fields_validate_on_shipped_kb(real_documents):
    """If any doctor entry failed validation, `load()` would have
    raised. Reaching this assertion means every one of the 12 records
    passed Pydantic validation."""
    doctor_docs = [d for d in real_documents if d.document_type == "doctor"]
    # A completeness check on the fields that matter for downstream
    # rendering / retrieval:
    for doc in doctor_docs:
        assert doc.title  # "Name — Specialization"
        assert "Doctor:" in doc.text
        assert "Specialization:" in doc.text
        assert "Services:" in doc.text
        assert "Biography:" in doc.text
        assert doc.metadata["doctor_id"] == doc.document_id


# ---------------------------------------------------------------------------
# 7 + 8: renderer determinism + availability disclaimer
# ---------------------------------------------------------------------------


def test_doctor_renderer_is_deterministic():
    doctor = DoctorKnowledge(
        doctor_id="DOC-Z01",
        name="Dr. Deterministic",
        specialization="Test",
        qualifications=["MBBS", "PhD"],
        experience_years=10,
        services=["Consultation"],
        consultation_fee_pkr=1234,
        available_days_summary="Sunday 4:00 PM - 6:00 PM",
        clinic_room="Room 999",
        languages=["English"],
        bio="A stable, deterministic biography.",
        demo_only=False,
    )
    a = render_doctor(doctor)
    b = render_doctor(doctor)
    assert a == b


def test_renderer_labels_availability_as_informational_only():
    """The `available_days_summary` field must NOT be presented as
    authoritative booking data — the renderer must explicitly frame
    it as informational so the LLM (and any reader) sees the caveat
    on every doctor chunk."""
    doctor = DoctorKnowledge(
        doctor_id="DOC-Z02",
        name="Dr. Caveat",
        specialization="Test",
        qualifications=["MBBS"],
        experience_years=1,
        services=["Consultation"],
        consultation_fee_pkr=1000,
        available_days_summary="Monday 9:00 AM - 5:00 PM",
        clinic_room="Room 12",
        languages=["English"],
        bio="Bio.",
        demo_only=False,
    )
    text = render_doctor(doctor)
    assert "informational only" in text
    assert "appointment system" in text


def test_renderer_flags_demo_only_doctors():
    demo_doctor = DoctorKnowledge(
        doctor_id="DOC-Z03",
        name="Dr. Demo",
        specialization="Test",
        qualifications=["MBBS"],
        experience_years=1,
        services=["Consultation"],
        consultation_fee_pkr=1000,
        available_days_summary="Monday 9:00 AM - 5:00 PM",
        clinic_room="Room 12",
        languages=["English"],
        bio="Bio.",
        demo_only=True,
    )
    text = render_doctor(demo_doctor)
    assert "demo-only" in text
    assert "not yet bookable" in text


# ---------------------------------------------------------------------------
# 9-11: policies / faq / loader return type
# ---------------------------------------------------------------------------


def test_clinic_policies_markdown_loads_successfully(real_documents):
    policies = [d for d in real_documents if d.document_type == "policy"]
    assert len(policies) == 1
    assert policies[0].source == "clinic_policies.md"
    assert policies[0].document_id == "clinic_policies"
    assert len(policies[0].text) > 500


def test_faq_markdown_loads_successfully(real_documents):
    faq = [d for d in real_documents if d.document_type == "faq"]
    assert len(faq) == 1
    assert faq[0].source == "faq.md"
    assert faq[0].document_id == "faq"
    assert len(faq[0].text) > 500


def test_loader_returns_knowledge_document_instances(real_documents):
    assert real_documents
    assert all(isinstance(d, KnowledgeDocument) for d in real_documents)
    # Frozen models — attempting to mutate should raise, proving the
    # downstream pipeline can't accidentally rewrite a document.
    with pytest.raises((TypeError, ValueError)):
        real_documents[0].text = "tampered"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 12: missing file → clear error
# ---------------------------------------------------------------------------


def test_missing_directory_raises_clear_error(tmp_path):
    with pytest.raises(KnowledgeLoadError, match="Knowledge directory does not exist"):
        DocumentLoader(tmp_path / "nope").load()


def test_missing_doctors_yaml_raises_clear_error(tmp_path):
    (tmp_path / "clinic_policies.md").write_text("# x\n\ny", encoding="utf-8")
    (tmp_path / "faq.md").write_text("# x\n\ny", encoding="utf-8")
    with pytest.raises(KnowledgeLoadError, match="doctors.yaml"):
        DocumentLoader(tmp_path).load()


def test_missing_policies_markdown_raises_clear_error(tmp_path):
    _write_minimal_kb(tmp_path)
    (tmp_path / "clinic_policies.md").unlink()
    with pytest.raises(KnowledgeLoadError, match="clinic_policies.md"):
        DocumentLoader(tmp_path).load()


def test_missing_faq_markdown_raises_clear_error(tmp_path):
    _write_minimal_kb(tmp_path)
    (tmp_path / "faq.md").unlink()
    with pytest.raises(KnowledgeLoadError, match="faq.md"):
        DocumentLoader(tmp_path).load()


# ---------------------------------------------------------------------------
# 13-15: duplicate ids, invalid data, empty markdown
# ---------------------------------------------------------------------------


def test_duplicate_doctor_id_is_rejected(tmp_path):
    bad_yaml = dedent(
        """\
        doctors:
          - doctor_id: DOC-DUP
            name: Dr. First
            specialization: General Medicine
            qualifications: [MBBS]
            experience_years: 5
            services: [Consultation]
            consultation_fee_pkr: 1500
            available_days_summary: "Monday"
            clinic_room: "Room 1"
            languages: [Urdu]
            bio: "First."
            demo_only: true
          - doctor_id: DOC-DUP
            name: Dr. Second
            specialization: Dermatology
            qualifications: [MBBS]
            experience_years: 5
            services: [Consultation]
            consultation_fee_pkr: 1500
            available_days_summary: "Tuesday"
            clinic_room: "Room 2"
            languages: [English]
            bio: "Second."
            demo_only: true
        """
    )
    _write_minimal_kb(tmp_path, doctors_yaml=bad_yaml)
    with pytest.raises(KnowledgeLoadError, match="duplicate doctor_id"):
        DocumentLoader(tmp_path).load()


def test_invalid_doctor_data_is_rejected(tmp_path):
    # experience_years < 0 violates the DoctorKnowledge schema.
    bad_yaml = dedent(
        """\
        doctors:
          - doctor_id: DOC-BAD
            name: Dr. Bad
            specialization: General Medicine
            qualifications: [MBBS]
            experience_years: -3
            services: [Consultation]
            consultation_fee_pkr: 1500
            available_days_summary: "Monday"
            clinic_room: "Room 1"
            languages: [Urdu]
            bio: "Bio."
            demo_only: true
        """
    )
    _write_minimal_kb(tmp_path, doctors_yaml=bad_yaml)
    with pytest.raises(KnowledgeLoadError, match="DOC-BAD"):
        DocumentLoader(tmp_path).load()


def test_empty_qualifications_list_is_rejected(tmp_path):
    bad_yaml = dedent(
        """\
        doctors:
          - doctor_id: DOC-EMPTY
            name: Dr. Empty
            specialization: General Medicine
            qualifications: []
            experience_years: 5
            services: [Consultation]
            consultation_fee_pkr: 1500
            available_days_summary: "Monday"
            clinic_room: "Room 1"
            languages: [Urdu]
            bio: "Bio."
            demo_only: true
        """
    )
    _write_minimal_kb(tmp_path, doctors_yaml=bad_yaml)
    with pytest.raises(KnowledgeLoadError, match="DOC-EMPTY"):
        DocumentLoader(tmp_path).load()


def test_empty_markdown_is_rejected(tmp_path):
    _write_minimal_kb(tmp_path)
    (tmp_path / "clinic_policies.md").write_text("   \n  \n", encoding="utf-8")
    with pytest.raises(KnowledgeLoadError, match="clinic_policies.md is empty"):
        DocumentLoader(tmp_path).load()


def test_malformed_yaml_is_rejected(tmp_path):
    _write_minimal_kb(tmp_path)
    (tmp_path / "doctors.yaml").write_text(
        "doctors:\n  - doctor_id: DOC-1\n    :bad indent\n", encoding="utf-8"
    )
    with pytest.raises(KnowledgeLoadError, match="Invalid YAML"):
        DocumentLoader(tmp_path).load()


def test_yaml_without_top_level_doctors_key_is_rejected(tmp_path):
    _write_minimal_kb(tmp_path)
    (tmp_path / "doctors.yaml").write_text("something_else: []\n", encoding="utf-8")
    with pytest.raises(KnowledgeLoadError, match="top-level 'doctors' key"):
        DocumentLoader(tmp_path).load()


# ---------------------------------------------------------------------------
# Round-trip: build a synthetic KB from scratch and load it cleanly.
# ---------------------------------------------------------------------------


def test_synthetic_knowledge_base_round_trips(tmp_path):
    _write_minimal_kb(tmp_path)
    docs = DocumentLoader(tmp_path).load()
    # 1 doctor + 1 policy + 1 faq
    assert len(docs) == 3
    types = {d.document_type for d in docs}
    assert types == {"doctor", "policy", "faq"}


def test_loader_output_is_sorted_by_document_id(real_documents):
    doctor_docs = [d for d in real_documents if d.document_type == "doctor"]
    ids = [d.document_id for d in doctor_docs]
    assert ids == sorted(ids)


def test_availability_summary_from_yaml_is_not_treated_as_bookable(real_documents):
    """The renderer's disclaimer must be present on EVERY doctor
    document so an LLM reading the retrieved chunks can't be tricked
    into thinking the availability line is an appointment fact."""
    doctor_docs = [d for d in real_documents if d.document_type == "doctor"]
    for doc in doctor_docs:
        assert "informational only" in doc.text
        assert "appointment system" in doc.text


def test_shipped_doc_001_and_doc_002_are_not_flagged_demo_only(real_documents):
    """Excel-backed doctors must have `demo_only=False` in metadata
    so downstream code can filter for actually-bookable profiles."""
    by_id = {
        d.document_id: d for d in real_documents if d.document_type == "doctor"
    }
    assert by_id["DOC-001"].metadata["demo_only"] is False
    assert by_id["DOC-002"].metadata["demo_only"] is False


# ---------------------------------------------------------------------------
# The Pydantic model's extra=forbid gate — catches YAML typos early
# ---------------------------------------------------------------------------


def test_unknown_doctor_field_is_rejected(tmp_path):
    bad_yaml = dedent(
        """\
        doctors:
          - doctor_id: DOC-TYPO
            name: Dr. Typo
            specialization: General Medicine
            qualifications: [MBBS]
            experience_years: 5
            services: [Consultation]
            consultation_fee_pkr: 1500
            available_days_summary: "Monday"
            clinic_room: "Room 1"
            languages: [Urdu]
            bio: "Bio."
            demo_only: true
            typo_field: should not be here
        """
    )
    _write_minimal_kb(tmp_path, doctors_yaml=bad_yaml)
    with pytest.raises(KnowledgeLoadError, match="DOC-TYPO"):
        DocumentLoader(tmp_path).load()


def test_yaml_direct_pydantic_validation_smoke():
    """Sanity: DoctorKnowledge validates a hand-built dict independent
    of the loader path."""
    data = {
        "doctor_id": "DOC-S01",
        "name": "Dr. Smoke",
        "specialization": "Test",
        "qualifications": ["MBBS"],
        "experience_years": 3,
        "services": ["Consultation"],
        "consultation_fee_pkr": 900,
        "available_days_summary": "Monday",
        "clinic_room": "Room 1",
        "languages": ["English"],
        "bio": "Bio.",
        "demo_only": True,
    }
    assert DoctorKnowledge.model_validate(data).doctor_id == "DOC-S01"
    # Round-trip through YAML too — proves the YAML loader path is
    # exercised the same way.
    parsed = yaml.safe_load(yaml.safe_dump(data))
    assert DoctorKnowledge.model_validate(parsed).doctor_id == "DOC-S01"
