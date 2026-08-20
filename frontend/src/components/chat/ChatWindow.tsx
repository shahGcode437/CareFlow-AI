import { useMemo, useRef, useState } from "react";
import {
  RefreshCw,
  Settings2,
  Sparkles,
} from "lucide-react";
import { ChatComposer, type ChatComposerHandle } from "./ChatComposer";
import { MessageBubble } from "./MessageBubble";
import { MessageList } from "./MessageList";
import { TypingIndicator } from "./TypingIndicator";
import { SuggestedPrompts } from "./SuggestedPrompts";
import { StaffReviewBanner } from "./StaffReviewBanner";
import { PatientPhoneField } from "./PatientPhoneField";
import { IntentCardRouter } from "./cards/IntentCardRouter";
import { ApiErrorAlert } from "@/components/feedback/ApiErrorAlert";
import { useChatSession, type ChatMessage } from "@/hooks/useChatSession";
import { cn } from "@/lib/utils";

/**
 * Top-level container for the AI Assistant experience.
 *
 * Owns the session hook, threads the composer imperative handle
 * through to each message row (so a NeedsInfoCard / AlternativeSlot
 * card can hand text back to the composer), and coordinates the two
 * subtle mode-switches:
 *
 *   - Empty transcript → welcome + suggested prompts
 *   - Populated transcript → message list + typing indicator
 */
export function ChatWindow() {
  const session = useChatSession();
  const composerRef = useRef<ChatComposerHandle>(null);
  const [showSettings, setShowSettings] = useState(false);

  const isEmpty = session.messages.length === 0;

  function handleSend(text: string) {
    void session.send(text);
  }

  function handlePromptSelect(prompt: string) {
    composerRef.current?.setValueAndFocus(prompt);
  }

  // Find the most recent user message — used by NeedsInfoCard so the
  // user can rephrase what they said, not what the assistant said.
  const lastUserMessage = useMemo<string | null>(() => {
    for (let i = session.messages.length - 1; i >= 0; i--) {
      const m = session.messages[i];
      if (m.role === "user") return m.text;
    }
    return null;
  }, [session.messages]);

  return (
    <div
      className={cn(
        "flex h-[calc(100dvh-13rem)] min-h-[520px] flex-col overflow-hidden rounded-2xl border border-border bg-surface",
        "sm:h-[calc(100dvh-14rem)]",
      )}
    >
      {/* ---------------------------------------------------------------- */}
      {/* Chat header                                                       */}
      {/* ---------------------------------------------------------------- */}
      <header className="flex items-center justify-between gap-3 border-b border-border bg-card px-4 py-3 sm:px-5">
        <div className="flex min-w-0 items-center gap-3">
          <span
            aria-hidden="true"
            className="inline-flex size-9 flex-shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground"
          >
            <Sparkles className="size-4" strokeWidth={1.75} />
          </span>
          <div className="min-w-0">
            <div className="truncate text-sm font-semibold tracking-tight text-foreground">
              CareFlow AI
            </div>
            <div className="text-[11px] text-muted-foreground">
              {session.pending ? "Thinking…" : "Ready when you are"}
              {session.patientPhone && (
                <>
                  {" · "}
                  <span className="font-mono">{session.patientPhone}</span>
                </>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-1">
          {session.messages.length > 0 && (
            <button
              type="button"
              onClick={session.clear}
              disabled={session.pending}
              aria-label="Start a new session"
              className={cn(
                "inline-flex size-9 items-center justify-center rounded-md text-muted-foreground",
                "hover:bg-muted hover:text-foreground",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                "disabled:cursor-not-allowed disabled:opacity-60",
              )}
            >
              <RefreshCw className="size-4" strokeWidth={1.75} />
            </button>
          )}
          <button
            type="button"
            onClick={() => setShowSettings((s) => !s)}
            aria-expanded={showSettings}
            aria-controls="chat-session-settings"
            aria-label="Session settings"
            className={cn(
              "inline-flex size-9 items-center justify-center rounded-md text-muted-foreground",
              "hover:bg-muted hover:text-foreground",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              showSettings && "bg-muted text-foreground",
            )}
          >
            <Settings2 className="size-4" strokeWidth={1.75} />
          </button>
        </div>
      </header>

      {/* ---------------------------------------------------------------- */}
      {/* Optional settings drawer                                           */}
      {/* ---------------------------------------------------------------- */}
      {showSettings && (
        <div id="chat-session-settings" className="border-b border-border bg-card px-4 py-4 sm:px-5">
          <PatientPhoneField
            value={session.patientPhone}
            onChange={session.setPatientPhone}
          />
        </div>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Body: welcome OR message list                                     */}
      {/* ---------------------------------------------------------------- */}
      {isEmpty ? (
        <WelcomeState
          onSelect={handlePromptSelect}
          disabled={session.pending}
        />
      ) : (
        <MessageList scrollTrigger={session.messages.length + (session.pending ? 1 : 0)}>
          {session.messages.map((m) => (
            <RenderedMessage
              key={m.id}
              message={m}
              lastUserMessage={lastUserMessage}
              onPrefillComposer={(text) => composerRef.current?.setValueAndFocus(text)}
              onRetry={() => void session.retry(m.id)}
              pending={session.pending}
            />
          ))}
          {session.pending && (
            <div className="flex justify-start">
              <TypingIndicator />
            </div>
          )}
        </MessageList>
      )}

      {/* ---------------------------------------------------------------- */}
      {/* Composer                                                          */}
      {/* ---------------------------------------------------------------- */}
      <div
        className={cn(
          "border-t border-border bg-card px-3 py-3 sm:px-5 sm:py-4",
          // iOS keyboard safe area on mobile
          "pb-[calc(env(safe-area-inset-bottom)+0.75rem)]",
        )}
      >
        <ChatComposer
          ref={composerRef}
          onSend={handleSend}
          disabled={session.pending}
        />
        <p className="mt-2 text-[11px] text-muted-foreground">
          Enter to send · Shift+Enter for a new line. Session id is
          generated client-side; the backend is stateless.
        </p>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Welcome state                                                       */
/* ------------------------------------------------------------------ */

function WelcomeState({
  onSelect,
  disabled,
}: {
  onSelect: (prompt: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6 sm:py-10">
      <div className="mx-auto max-w-2xl">
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-primary">
          <Sparkles className="size-3.5" strokeWidth={2} />
          AI Assistant
        </div>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
          What can CareFlow help you with today?
        </h2>
        <p className="mt-2 text-sm text-muted-foreground sm:text-base">
          Ask about a doctor's availability, book an appointment, look
          one up, or make a change — plain language works. CareFlow only
          uses tools it's approved to call; nothing is fabricated.
        </p>
        <div className="mt-6">
          <SuggestedPrompts onSelect={onSelect} disabled={disabled} />
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Individual message rendering                                        */
/* ------------------------------------------------------------------ */

function RenderedMessage({
  message,
  lastUserMessage,
  onPrefillComposer,
  onRetry,
  pending,
}: {
  message: ChatMessage;
  lastUserMessage: string | null;
  onPrefillComposer: (text: string) => void;
  onRetry: () => void;
  pending: boolean;
}) {
  if (message.role === "user") {
    return (
      <MessageBubble
        role="user"
        text={message.text}
        timestamp={message.timestamp}
      />
    );
  }

  if (message.role === "assistant") {
    return (
      <MessageBubble
        role="assistant"
        text={message.text}
        timestamp={message.timestamp}
        attachment={
          <IntentCardRouter
            intent={message.intent}
            data={message.data}
            originalUserMessage={lastUserMessage}
            onUseSlot={onPrefillComposer}
            onRephrase={onPrefillComposer}
          />
        }
        footer={
          <>
            {message.requiresStaffReview && <StaffReviewBanner />}
            <div className="mt-1 text-[10px] font-mono text-muted-foreground">
              req · {message.requestId.slice(0, 8)}
            </div>
          </>
        }
      />
    );
  }

  // Error row — use ApiErrorAlert directly. Not a bubble; a first-class
  // banner so it stands apart from the conversation.
  return (
    <div className="flex justify-start">
      <ApiErrorAlert
        error={message.error}
        onRetry={pending ? undefined : onRetry}
      >
        <span className="text-xs text-muted-foreground">
          {"kind" in message.error &&
            typeof (message.error as { kind?: unknown }).kind === "string"
            ? null
            : null}
        </span>
      </ApiErrorAlert>
    </div>
  );
}
