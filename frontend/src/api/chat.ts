import { CHAT_TIMEOUT_MS, apiFetch } from "@/lib/apiClient";
import type { ChatRequest, ChatResponse } from "@/types/api";

/**
 * POST /chat — the Supervisor entry point.
 *
 * Uses the extended 30 s timeout because the agent may synchronously
 * wait on a Groq LLM call. `session_id` is accepted by the backend but
 * currently discarded (no conversation memory) — see
 * `backend/app/agents/supervisor.py`. Callers can still supply one so
 * a future memory upgrade needs no client change.
 */
export function sendChat(
  body: ChatRequest,
  signal?: AbortSignal,
): Promise<ChatResponse> {
  return apiFetch<ChatResponse, ChatRequest>("/chat", {
    method: "POST",
    body,
    timeoutMs: CHAT_TIMEOUT_MS,
    signal,
  });
}
