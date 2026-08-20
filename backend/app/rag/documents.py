"""Knowledge-document loader + Pydantic validation (Phase 8.8.3).

Reads the three sources under ``backend/data/knowledge/`` and returns a
deterministic list of :class:`KnowledgeDocument` objects. This layer
performs **validation and normalization only** — it does not chunk,
embed, or retrieve. Those responsibilities land in later phases
(``chunker.py``, ``embedder.py``, ``vector_store.py``, ``retriever.py``).

Framework-independent by design (matching the pattern established in
``app/tools/__init__.py``): no LangChain, no LlamaIndex.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator


# ---------------------------------------------------------------------------
# Public error
# ---------------------------------------------------------------------------


class KnowledgeLoadError(Exception):
    """Raised for every deterministic failure encountered while loading
    the clinic knowledge base — missing files, invalid YAML/Markdown,
    duplicate identifiers, or Pydantic validation failures. Callers
    should surface :attr:`args[0]` as the user-facing reason string.
    """


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class DoctorKnowledge(BaseModel):
    """One entry from ``doctors.yaml``. Field names mirror the YAML
    exactly so an authoring mistake surfaces at load time.
    """

    doctor_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    specialization: str = Field(..., min_length=1)
    qualifications: list[str] = Field(..., min_length=1)
    experience_years: int = Field(..., ge=0)
    services: list[str] = Field(..., min_length=1)
    consultation_fee_pkr: int = Field(..., ge=0)
    available_days_summary: str = Field(..., min_length=1)
    clinic_room: str = Field(..., min_length=1)
    languages: list[str] = Field(..., min_length=1)
    bio: str = Field(..., min_length=1)
    demo_only: bool

    model_config = {"extra": "forbid"}

    @field_validator("qualifications", "services", "languages")
    @classmethod
    def _strip_list_items(cls, value: list[str]) -> list[str]:
        cleaned = [v.strip() for v in value if isinstance(v, str)]
        if any(len(v) == 0 for v in cleaned):
            raise ValueError("list items must be non-empty strings")
        return cleaned

    @field_validator("bio")
    @classmethod
    def _strip_bio(cls, value: str) -> str:
        return value.strip()


DocumentType = Literal["doctor", "policy", "faq"]


class KnowledgeDocument(BaseModel):
    """Normalized document ready for the future chunker + retriever.

    Everything the downstream pipeline needs is here: which file it
    came from (``source``), what kind of document it is
    (``document_type``), a stable identifier (``document_id``), a
    short human-readable ``title`` for UI display, the ``text`` payload
    that will be chunked and embedded, and structured ``metadata`` for
    filtering and citation display.
    """

    source: str = Field(..., min_length=1)
    document_type: DocumentType
    document_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    metadata: dict[str, str | int | bool] = Field(default_factory=dict)

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# Deterministic doctor renderer
# ---------------------------------------------------------------------------


def render_doctor(doctor: DoctorKnowledge) -> str:
    """Render a DoctorKnowledge record as a stable text block.

    The output is deterministic (same input → identical bytes), so
    embeddings and tests are reproducible. The `Availability Summary`
    line is labelled clearly to remind callers that it is
    informational knowledge — actual appointment availability is
    determined by the Appointment Service, not by this text.
    """

    lines: list[str] = [
        f"Doctor: {doctor.name}",
        f"Doctor ID: {doctor.doctor_id}",
        f"Specialization: {doctor.specialization}",
        f"Qualifications: {', '.join(doctor.qualifications)}",
        f"Experience: {doctor.experience_years} years",
        f"Services: {', '.join(doctor.services)}",
        f"Consultation Fee: PKR {doctor.consultation_fee_pkr}",
        (
            f"Availability Summary (informational only; "
            f"actual bookable slots come from the appointment system): "
            f"{doctor.available_days_summary}"
        ),
        f"Clinic Room: {doctor.clinic_room}",
        f"Languages: {', '.join(doctor.languages)}",
        f"Biography: {doctor.bio}",
    ]
    if doctor.demo_only:
        lines.append(
            "Note: this is a demo-only profile; the doctor is not yet "
            "bookable through the appointment system."
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


_DOCTORS_FILE = "doctors.yaml"
_POLICIES_FILE = "clinic_policies.md"
_FAQ_FILE = "faq.md"


class DocumentLoader:
    """Load and validate the clinic knowledge base.

    Usage::

        loader = DocumentLoader(Path("backend/data/knowledge"))
        documents = loader.load()

    :meth:`load` is the only public entry point. It reads all three
    knowledge sources, validates them, and returns a **deterministic**
    list of :class:`KnowledgeDocument` — sorted by document type first
    (``doctor`` → ``policy`` → ``faq``) and by ``document_id`` within
    each type. The ordering is stable so downstream chunk indices and
    tests are reproducible.
    """

    def __init__(self, base_dir: Path | str):
        self._base_dir = Path(base_dir)

    # -- public --------------------------------------------------------------

    def load(self) -> list[KnowledgeDocument]:
        if not self._base_dir.exists():
            raise KnowledgeLoadError(
                f"Knowledge directory does not exist: {self._base_dir}"
            )
        if not self._base_dir.is_dir():
            raise KnowledgeLoadError(
                f"Knowledge path is not a directory: {self._base_dir}"
            )

        doctors = self._load_doctors()
        policies = self._load_policies()
        faq = self._load_faq()

        return doctors + [policies, faq]

    # -- doctors -------------------------------------------------------------

    def _load_doctors(self) -> list[KnowledgeDocument]:
        path = self._require_file(_DOCTORS_FILE)

        try:
            raw: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise KnowledgeLoadError(f"Invalid YAML in {path.name}: {exc}") from exc

        if not isinstance(raw, dict) or "doctors" not in raw:
            raise KnowledgeLoadError(
                f"{path.name} must be a mapping with a top-level 'doctors' key."
            )
        entries = raw["doctors"]
        if not isinstance(entries, list) or len(entries) == 0:
            raise KnowledgeLoadError(
                f"{path.name} must contain a non-empty 'doctors' list."
            )

        validated: list[DoctorKnowledge] = []
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                raise KnowledgeLoadError(
                    f"{path.name} doctor entry #{index} is not a mapping."
                )
            try:
                validated.append(DoctorKnowledge.model_validate(entry))
            except ValidationError as exc:
                doctor_id = entry.get("doctor_id", f"<index {index}>")
                raise KnowledgeLoadError(
                    f"{path.name} doctor '{doctor_id}' failed validation: {exc}"
                ) from exc

        seen: dict[str, int] = {}
        for i, d in enumerate(validated):
            if d.doctor_id in seen:
                raise KnowledgeLoadError(
                    f"{path.name} contains duplicate doctor_id "
                    f"'{d.doctor_id}' at entries #{seen[d.doctor_id]} and #{i}."
                )
            seen[d.doctor_id] = i

        documents = [
            KnowledgeDocument(
                source=_DOCTORS_FILE,
                document_type="doctor",
                document_id=d.doctor_id,
                title=f"{d.name} — {d.specialization}",
                text=render_doctor(d),
                metadata={
                    "doctor_id": d.doctor_id,
                    "name": d.name,
                    "specialization": d.specialization,
                    "demo_only": d.demo_only,
                },
            )
            for d in validated
        ]
        # Stable ordering — sorted by document_id (which is also
        # doctor_id) so tests can assert positions.
        return sorted(documents, key=lambda doc: doc.document_id)

    # -- policies / faq ------------------------------------------------------

    def _load_policies(self) -> KnowledgeDocument:
        return self._load_markdown(
            filename=_POLICIES_FILE,
            document_type="policy",
            document_id="clinic_policies",
            title="Clinic Policies",
        )

    def _load_faq(self) -> KnowledgeDocument:
        return self._load_markdown(
            filename=_FAQ_FILE,
            document_type="faq",
            document_id="faq",
            title="Clinic FAQ",
        )

    def _load_markdown(
        self,
        *,
        filename: str,
        document_type: DocumentType,
        document_id: str,
        title: str,
    ) -> KnowledgeDocument:
        path = self._require_file(filename)
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            raise KnowledgeLoadError(f"{filename} is empty.")
        return KnowledgeDocument(
            source=filename,
            document_type=document_type,
            document_id=document_id,
            title=title,
            text=text,
            metadata={},
        )

    # -- helpers -------------------------------------------------------------

    def _require_file(self, filename: str) -> Path:
        path = self._base_dir / filename
        if not path.exists():
            raise KnowledgeLoadError(
                f"Required knowledge file is missing: {path}"
            )
        if not path.is_file():
            raise KnowledgeLoadError(
                f"Expected a file for {filename}, found a directory: {path}"
            )
        return path


__all__ = [
    "DocumentLoader",
    "DoctorKnowledge",
    "KnowledgeDocument",
    "KnowledgeLoadError",
    "render_doctor",
]
