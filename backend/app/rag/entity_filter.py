"""Entity-aware retrieval filtering and reranking (Phase 9.1).

Eliminates cross-doctor noise when answering single-doctor questions
(e.g., "Who is Dr. Ahmed?", "What is Dr. Sara's specialization?").

When the query identifies exactly ONE doctor entity:
  * Only doctor chunks for that target doctor are preserved.
  * Unrelated doctor chunks are removed so they do not pollute the answer.
  * Policy / FAQ chunks are preserved (supporting mixed queries like
    "What is Dr. Ahmed's cancellation policy?").
  * The target doctor chunk is prioritized at the front of the results.

When the query is genuinely broad ("Which doctors are available?",
"Who are the cardiologists?", "What specialties do you have?"):
  * No single-doctor restriction is applied; standard similarity-ranked
    results are returned as-is.

When the query mentions an explicit UNKNOWN doctor ("Who is Dr. Xyz?"):
  * All doctor chunks are treated as unrelated and filtered out, leading
    to an honest "information not in knowledge base" response.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from app.rag.chunker import KnowledgeChunk
from app.rag.vector_store import VectorSearchResult


# ---------------------------------------------------------------------------
# Pre-configured clinic doctor entity registry (DOC-001 through DOC-012)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DoctorEntity:
    doctor_id: str
    name: str
    tokens: tuple[str, ...]


CLINIC_DOCTORS: tuple[DoctorEntity, ...] = (
    DoctorEntity(
        doctor_id="DOC-001",
        name="Dr. Ahmed",
        tokens=("ahmed",),
    ),
    DoctorEntity(
        doctor_id="DOC-002",
        name="Dr. Sara",
        tokens=("sara",),
    ),
    DoctorEntity(
        doctor_id="DOC-003",
        name="Dr. Bilal Iqbal",
        tokens=("bilal iqbal", "bilal", "iqbal"),
    ),
    DoctorEntity(
        doctor_id="DOC-004",
        name="Dr. Nadia Malik",
        tokens=("nadia malik", "nadia", "malik"),
    ),
    DoctorEntity(
        doctor_id="DOC-005",
        name="Dr. Ayesha Rehman",
        tokens=("ayesha rehman", "ayesha", "rehman"),
    ),
    DoctorEntity(
        doctor_id="DOC-006",
        name="Dr. Kashif Zafar",
        tokens=("kashif zafar", "kashif", "zafar"),
    ),
    DoctorEntity(
        doctor_id="DOC-007",
        name="Dr. Faisal Butt",
        tokens=("faisal butt", "faisal", "butt"),
    ),
    DoctorEntity(
        doctor_id="DOC-008",
        name="Dr. Zainab Qureshi",
        tokens=("zainab qureshi", "zainab", "qureshi"),
    ),
    DoctorEntity(
        doctor_id="DOC-009",
        name="Dr. Hassan Ali",
        tokens=("hassan ali", "hassan", "ali"),
    ),
    DoctorEntity(
        doctor_id="DOC-010",
        name="Dr. Mariam Siddiqui",
        tokens=("mariam siddiqui", "mariam", "siddiqui"),
    ),
    DoctorEntity(
        doctor_id="DOC-011",
        name="Dr. Usman Tariq",
        tokens=("usman tariq", "usman", "tariq"),
    ),
    DoctorEntity(
        doctor_id="DOC-012",
        name="Dr. Rabia Farooq",
        tokens=("rabia farooq", "rabia", "farooq"),
    ),
)

# Words following "Dr." or "Doctor" that represent general concepts rather
# than unknown doctor surnames.
_EXCLUDED_TITLE_WORDS = frozenset(
    {
        "appointment",
        "appointments",
        "availability",
        "schedule",
        "profile",
        "profiles",
        "list",
        "fees",
        "fee",
        "timings",
        "timing",
        "hours",
        "hour",
        "service",
        "services",
        "specialist",
        "specialists",
        "specialty",
        "specialties",
        "consultation",
        "consultations",
        "visit",
        "visits",
        "booking",
        "bookings",
        "name",
        "names",
        "info",
        "information",
        "details",
        "recommendation",
        "recommendations",
        "advice",
        "help",
    }
)

_DR_TITLE_RE = re.compile(
    r"\b(?:dr\.?|doctor)\s+([a-zA-Z]+(?:\s+[a-zA-Z]+)?)\b", re.IGNORECASE
)
_DOC_ID_RE = re.compile(r"\bdoc-?0*([1-9]|1[0-2])\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Entity detection helper
# ---------------------------------------------------------------------------


def detect_doctor_entities(
    query: str,
    registry: Sequence[DoctorEntity] = CLINIC_DOCTORS,
) -> tuple[set[str], bool]:
    """Detect explicit doctor references in ``query``.

    Returns:
      (matched_doctor_ids, is_unknown_doctor)

      - matched_doctor_ids: set of normalized doctor_id strings (e.g. {"DOC-001"})
      - is_unknown_doctor: True if the query explicitly requested an unknown
        doctor (e.g. "Who is Dr. Xyz?").
    """
    cleaned = query.strip()
    if not cleaned:
        return set(), False

    matched_ids: set[str] = set()

    # 1. Match by explicit DOC-XXX ID (e.g., "DOC-001", "doc-1", "DOC002")
    for m in _DOC_ID_RE.finditer(cleaned):
        num = int(m.group(1))
        # Find matching in registry or default 3-digit format
        candidate_id = f"DOC-{num:03d}" if num < 10 else f"DOC-{num:03d}"
        if num == 10:
            candidate_id = "DOC-010"
        matched_ids.add(candidate_id)

    # 2. Match by known doctor name tokens with boundary and optional possessive
    lowered = cleaned.lower()
    for doc in registry:
        for tok in doc.tokens:
            pattern = r"\b" + re.escape(tok) + r"(?:['’]s)?\b"
            if re.search(pattern, lowered):
                matched_ids.add(doc.doctor_id)
                break

    # 3. Check for explicit unknown doctor mentions (e.g. "Dr. Xyz", "Doctor Watson")
    is_unknown_doctor = False
    if not matched_ids:
        for m in _DR_TITLE_RE.finditer(cleaned):
            name_candidate = m.group(1).lower().strip()
            first_word = name_candidate.split()[0]
            if first_word not in _EXCLUDED_TITLE_WORDS:
                # Check if it matches any known doctor
                matched = any(
                    any(tok in name_candidate for tok in d.tokens)
                    for d in registry
                )
                if not matched:
                    is_unknown_doctor = True
                    break

    return matched_ids, is_unknown_doctor


# ---------------------------------------------------------------------------
# Filter and rerank
# ---------------------------------------------------------------------------


def filter_and_rerank_results(
    results: list[VectorSearchResult],
    query: str,
    *,
    top_k: int = 4,
    registry: Sequence[DoctorEntity] = CLINIC_DOCTORS,
) -> list[VectorSearchResult]:
    """Filter and rerank retrieval results based on entity context in ``query``.

    Rules:
      1. Single known doctor identified:
         - Keep doctor chunks matching the target doctor.
         - Drop all OTHER doctor chunks (eliminating cross-doctor noise).
         - Keep non-doctor chunks (policy/faq).
         - Prioritize target doctor chunk at the front.
      2. Explicit unknown doctor identified (e.g. "Dr. Xyz"):
         - Drop ALL doctor chunks (all existing doctors are unrelated).
         - Keep non-doctor chunks (if any met similarity threshold).
      3. Multiple known doctors identified:
         - Keep doctor chunks matching ANY of the identified doctors.
         - Drop unrelated doctor chunks.
      4. Broad / no doctor identified:
         - Return results in original similarity order without filtering.
    """
    if not results:
        return []

    matched_ids, is_unknown = detect_doctor_entities(query, registry=registry)

    # Case 1: Exactly one doctor requested
    if len(matched_ids) == 1:
        target_id = next(iter(matched_ids))
        target_doctor_hits = [
            r
            for r in results
            if r.chunk.document_type == "doctor"
            and (
                r.chunk.metadata.get("doctor_id") == target_id
                or r.chunk.document_id == target_id
                or r.chunk.chunk_id == f"doctor:{target_id}"
            )
        ]
        non_doctor_hits = [
            r for r in results if r.chunk.document_type != "doctor"
        ]
        # Prioritize target doctor chunk first, followed by relevant policy/FAQ
        combined = target_doctor_hits + non_doctor_hits
        return combined[:top_k]

    # Case 2: Explicit unknown doctor requested (e.g. "Dr. Xyz")
    if is_unknown:
        non_doctor_hits = [
            r for r in results if r.chunk.document_type != "doctor"
        ]
        return non_doctor_hits[:top_k]

    # Case 3: Multiple specific doctors requested (e.g. "Compare Dr. Ahmed and Dr. Sara")
    if len(matched_ids) > 1:
        target_doctor_hits = [
            r
            for r in results
            if r.chunk.document_type == "doctor"
            and (
                r.chunk.metadata.get("doctor_id") in matched_ids
                or r.chunk.document_id in matched_ids
                or r.chunk.chunk_id in {f"doctor:{did}" for did in matched_ids}
            )
        ]
        non_doctor_hits = [
            r for r in results if r.chunk.document_type != "doctor"
        ]
        combined = target_doctor_hits + non_doctor_hits
        return combined[:top_k]

    # Case 4: Broad query or no doctor entity specified
    return results[:top_k]


# _DR_TITLE_RE captures up to two words after "Dr."/"Doctor" so it can
# grab two-word surnames ("Dr. Bilal Iqbal"). That means a sentence
# like "Dr. Watson available today?" also captures "Watson available"
# as a two-word candidate. These words never appear as an actual
# second name-word in this clinic's registry, so trimming them off a
# captured candidate is safe display-only cleanup, not a matching
# change — `detect_doctor_entities`'s own matching logic is untouched.
_NON_NAME_SENTENCE_CONTINUATIONS = frozenset(
    {"available", "free", "today", "tomorrow", "now", "please", "here", "there", "around", "open"}
)


def extract_dr_title_name(query: str) -> str | None:
    """Return the raw name text following a "Dr."/"Doctor" title in
    ``query`` (e.g. "Xyz" from "Dr. Xyz"), or ``None`` if no such
    pattern is present, or if the word following the title is a known
    non-name concept (see ``_EXCLUDED_TITLE_WORDS``, e.g. "Dr.
    appointment").

    Used by the appointment-side doctor-name resolver
    (``app.agents.doctor_resolver``, Phase 9.6) to phrase an honest
    "I couldn't find a doctor named X" message when a patient names an
    unknown doctor. Purely additive — does not change
    ``detect_doctor_entities``'s own behavior or return shape.
    """
    m = _DR_TITLE_RE.search(query)
    if not m:
        return None
    name_candidate = m.group(1).strip()
    if not name_candidate:
        return None
    words = name_candidate.split()
    first_word = words[0].lower()
    if first_word in _EXCLUDED_TITLE_WORDS:
        return None
    if len(words) > 1 and words[1].lower() in _NON_NAME_SENTENCE_CONTINUATIONS:
        return words[0]
    return name_candidate


__all__ = [
    "CLINIC_DOCTORS",
    "DoctorEntity",
    "detect_doctor_entities",
    "extract_dr_title_name",
    "filter_and_rerank_results",
]
