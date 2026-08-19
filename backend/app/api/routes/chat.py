"""Chat HTTP route — API-001.

Implements FastAPI API Contract Specification v1.0 §4: the entry point
for natural-language patient requests. Deferred in Phase 6 (no agent
existed to back it); implemented now that the Agent Orchestration layer
(Phase 7) exists.

Thin by design: parse the request via the existing Phase 2
ChatRequest/ChatResponse schemas and delegate everything else to the
Supervisor. No intent classification, tool selection, or business logic
lives here.
"""

from fastapi import APIRouter, Depends

from app.agents.supervisor import Supervisor
from app.api.dependencies import get_supervisor
from app.api.schemas.common import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(body: ChatRequest, supervisor: Supervisor = Depends(get_supervisor)) -> ChatResponse:
    result = supervisor.handle_message(
        message=body.message,
        session_id=body.session_id,
        patient_phone=body.patient_phone,
    )
    return ChatResponse(**result)
