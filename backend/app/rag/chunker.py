"""Knowledge chunker (Phase 8.8.4).

Takes the deterministic :class:`KnowledgeDocument` objects from
``documents.py`` and produces smaller, retrieval-ready
:class:`KnowledgeChunk` objects.

Rules (matching the approved chunking design):

* **Doctor documents** — kept as ONE chunk each. A doctor profile is
  already small and semantically cohesive; splitting it would break
  the joint meaning of e.g. "specialization + services + fee".

* **Policy Markdown** — split by ATX headings (``#`` / ``##`` / ``###``).
  Each heading section (heading line + everything up to the next
  heading) becomes one chunk; the heading is preserved inside the
  chunk text so a retrieved snippet is self-explanatory. Sections whose
  body is empty (after stripping the heading) are silently skipped.

* **FAQ Markdown** — same heading-split rule. Because the FAQ file
  uses one ``##`` per question, this keeps each question paired with
  its answer in a single chunk.

The output is deterministic: identical input → identical chunks,
identical ordering, identical IDs. No LLM, no embeddings, no external
calls — this layer is pure text handling.
"""

from __future__ import annotations

import re
from typing import Sequence

from pydantic import BaseModel, Field

from app.rag.documents import KnowledgeDocument


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


class KnowledgeChunk(BaseModel):
    """One retrieval-ready piece of clinic knowledge.

    Metadata is a superset of the parent document's metadata plus any
    provenance fields the chunker itself adds (``section_title`` for
    Markdown chunks, ``chunk_index`` for the sibling ordinal within its
    parent document).
    """

    chunk_id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    document_type: str = Field(..., min_length=1)
    document_id: str = Field(..., min_length=1)
    metadata: dict[str, str | int | bool] = Field(default_factory=dict)

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def chunk_documents(
    documents: Sequence[KnowledgeDocument],
) -> list[KnowledgeChunk]:
    """Turn a sequence of KnowledgeDocument into KnowledgeChunk objects.

    Preserves the input ordering: chunks for the first document come
    first, in order, then the second document's chunks, and so on.
    Determinism guarantee — same documents in, same chunks out
    (including chunk_ids), byte-for-byte.
    """

    chunks: list[KnowledgeChunk] = []
    for document in documents:
        if document.document_type == "doctor":
            chunks.append(_chunk_doctor(document))
        elif document.document_type == "policy":
            chunks.extend(_chunk_markdown(document, id_prefix="policy"))
        elif document.document_type == "faq":
            chunks.extend(_chunk_markdown(document, id_prefix="faq"))
        else:
            # Future-proofing: skip unknown document_type silently
            # rather than crash. Log-worthy in production, not
            # throw-worthy — this keeps `chunk_documents` total.
            continue
    return chunks


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _chunk_doctor(document: KnowledgeDocument) -> KnowledgeChunk:
    """A doctor document maps to exactly one chunk. Metadata is
    inherited plus a ``chunk_index: 0`` marker for consistency with the
    Markdown chunks."""
    metadata = dict(document.metadata)
    metadata["chunk_index"] = 0
    return KnowledgeChunk(
        chunk_id=f"doctor:{document.document_id}",
        text=document.text,
        source=document.source,
        document_type=document.document_type,
        document_id=document.document_id,
        metadata=metadata,
    )


# ATX heading matcher: 1-6 leading '#', at least one space, then title.
# Setext headings (=== / ---) are intentionally NOT supported — the
# shipped knowledge base uses ATX only.
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def _chunk_markdown(
    document: KnowledgeDocument, *, id_prefix: str
) -> list[KnowledgeChunk]:
    """Split a Markdown document into one chunk per heading section."""
    sections = _split_by_headings(document.text)
    chunks: list[KnowledgeChunk] = []
    ordinal = 0
    for heading, body in sections:
        # Skip empty sections — a heading with no meaningful body.
        if not body.strip():
            continue
        ordinal += 1
        chunk_id = f"{id_prefix}:{document.document_id}:{ordinal:02d}"
        # Preserve the heading in the text so retrieved results remain
        # self-explanatory: reader sees the question / policy title
        # right at the top of the snippet.
        text = f"{heading}\n\n{body.strip()}"
        metadata: dict[str, str | int | bool] = dict(document.metadata)
        metadata["chunk_index"] = ordinal
        metadata["section_title"] = _strip_heading_markers(heading)
        chunks.append(
            KnowledgeChunk(
                chunk_id=chunk_id,
                text=text,
                source=document.source,
                document_type=document.document_type,
                document_id=document.document_id,
                metadata=metadata,
            )
        )
    return chunks


def _split_by_headings(text: str) -> list[tuple[str, str]]:
    """Return a list of ``(heading_line, body_text)`` pairs.

    Every line matching :data:`_HEADING_RE` starts a new section.
    Content before the first heading is dropped — the shipped
    Markdown files always begin with a heading, so no real content
    ends up in the pre-heading region.
    """
    sections: list[tuple[str, list[str]]] = []
    current_heading: str | None = None
    current_body: list[str] = []

    for raw_line in text.splitlines():
        if _HEADING_RE.match(raw_line):
            if current_heading is not None:
                sections.append((current_heading, current_body))
            current_heading = raw_line.rstrip()
            current_body = []
        else:
            if current_heading is not None:
                current_body.append(raw_line)
            # Lines before the first heading are ignored on purpose.

    if current_heading is not None:
        sections.append((current_heading, current_body))

    return [(h, "\n".join(body)) for h, body in sections]


def _strip_heading_markers(heading_line: str) -> str:
    match = _HEADING_RE.match(heading_line)
    return match.group(2).strip() if match else heading_line.strip()


__all__ = ["KnowledgeChunk", "chunk_documents"]
