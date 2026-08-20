"""Knowledge/RAG package for CareFlow AI.

Implements Master Specification SYS-02 (Knowledge/RAG Agent) and SYS-05
(Clinic Knowledge Store). This package is the source of clinic-facing
information — doctor profiles, policies, and FAQs — and later phases
will layer chunking, embeddings, and retrieval on top of the loader
implemented here.

Layering (built incrementally across Phase 8.8):

    Phase 8.8.3  documents.py    ← THIS STEP — loaders + Pydantic models
    Phase 8.8.4  chunker.py      ← splits documents into retrieval chunks
    Phase 8.8.5  embedder.py     ← ONNX-runtime embeddings (fastembed)
    Phase 8.8.6  vector_store.py ← in-memory numpy cosine index
    Phase 8.8.7  retriever.py    ← glues the pieces together

Nothing in this package touches the Excel appointment workbook or
the Appointment Service. Actual appointment availability remains
authoritative in the Appointment Service — the knowledge base is
informational, per Master Spec §8 and §11 of this phase's plan.
"""
