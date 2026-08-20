import { useCallback, useMemo, useRef, useState } from "react";
import { sendChat } from "@/api/chat";
import { ApiError } from "@/lib/apiClient";
import type { ChatIntent, ChatResponse } from "@/types/api";

/**
 * Chat session state — one hook owns everything the ChatWindow needs.
 *
 * Honest scope:
 *   - The backend is stateless. `session_id` is generated once client-
 *     side and sent with every request; the server currently ignores
 *     it (see `backend/app/agents/supervisor.py`). We still send it so
 *     future server-side memory doesn't require any client change.
 *   - `patient_phone` is optional and lives in memory only — we do not
 *     persist it to localStorage on purpose (privacy: PII stays local
 *     to the tab session).
 *   - Message history is a client-side transcript only. Reloading the
 *     page clears it — that reflects what the backend actually knows.
 */

export type ChatMessage =
  | {
      role: "user";
      id: string;
      text: string;
      timestamp: number;
    }
  | {
      role: "assistant";
      id: string;
      text: string;
      intent: ChatIntent;
      data: Record<string, unknown> | null;
      requiresStaffReview: boolean;
      requestId: string;
      timestamp: number;
    }
  | {
      role: "error";
      id: string;
      /** The user message we were replying to — for retry. */
      inReplyTo: string;
      error: ApiError | Error;
      timestamp: number;
    };

interface UseChatSessionResult {
  sessionId: string;
  patientPhone: string | null;
  setPatientPhone: (phone: string | null) => void;
  messages: ChatMessage[];
  pending: boolean;
  send: (text: string) => Promise<void>;
  retry: (errorMessageId: string) => Promise<void>;
  clear: () => void;
}

function newId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function useChatSession(): UseChatSessionResult {
  // Session id — stable for the lifetime of the mounted hook. `useRef`
  // over `useState` because we never intentionally regenerate it and
  // never render its value.
  const sessionIdRef = useRef<string>(newId());

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState(false);
  const [patientPhone, setPatientPhoneState] = useState<string | null>(null);

  const setPatientPhone = useCallback((phone: string | null) => {
    // Empty string → treated as unset.
    setPatientPhoneState(phone && phone.trim().length > 0 ? phone.trim() : null);
  }, []);

  const runSend = useCallback(
    async (text: string) => {
      const userMessage: ChatMessage = {
        role: "user",
        id: newId(),
        text,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setPending(true);

      try {
        const response: ChatResponse = await sendChat({
          message: text,
          session_id: sessionIdRef.current,
          patient_phone: patientPhone,
        });

        // The backend types `intent` as a free string. In practice
        // it's the closed set in `ChatIntent`; we cast rather than
        // reject unknown values so a new backend intent doesn't break
        // the chat — the router falls back to the generic card.
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            id: newId(),
            text: response.message,
            intent: response.intent as ChatIntent,
            data: response.data,
            requiresStaffReview: response.requires_staff_review,
            requestId: response.request_id,
            timestamp: Date.now(),
          },
        ]);
      } catch (err) {
        setMessages((prev) => [
          ...prev,
          {
            role: "error",
            id: newId(),
            inReplyTo: userMessage.id,
            error:
              err instanceof ApiError || err instanceof Error
                ? err
                : new Error("Unexpected error"),
            timestamp: Date.now(),
          },
        ]);
      } finally {
        setPending(false);
      }
    },
    [patientPhone],
  );

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || pending) return;
      await runSend(trimmed);
    },
    [pending, runSend],
  );

  const retry = useCallback(
    async (errorMessageId: string) => {
      if (pending) return;
      const errorMsg = messages.find(
        (m): m is Extract<ChatMessage, { role: "error" }> =>
          m.role === "error" && m.id === errorMessageId,
      );
      if (!errorMsg) return;
      const original = messages.find(
        (m): m is Extract<ChatMessage, { role: "user" }> =>
          m.role === "user" && m.id === errorMsg.inReplyTo,
      );
      if (!original) return;
      // Drop the error record and re-send.
      setMessages((prev) => prev.filter((m) => m.id !== errorMessageId));
      await runSend(original.text);
    },
    [messages, pending, runSend],
  );

  const clear = useCallback(() => {
    if (pending) return;
    setMessages([]);
  }, [pending]);

  return useMemo(
    () => ({
      sessionId: sessionIdRef.current,
      patientPhone,
      setPatientPhone,
      messages,
      pending,
      send,
      retry,
      clear,
    }),
    [patientPhone, setPatientPhone, messages, pending, send, retry, clear],
  );
}
