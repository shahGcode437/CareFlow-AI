import { Info, PencilLine } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Renders when the backend returns `intent === "needs_information"`.
 *
 * Important honest constraint: the backend is currently stateless —
 * `session_id` is accepted but discarded, so we cannot "just add the
 * missing piece" on the server side and continue an in-flight
 * conversation. The correct pattern is to re-send ONE complete
 * message with everything the tool needs.
 *
 * This card hands that job to the user in the friendliest way we can:
 * a "Rephrase and resend" button that copies the last user message
 * back into the composer for editing. The assistant's clarification
 * text (rendered in the bubble above) has already told them exactly
 * which fields are missing.
 */
export function NeedsInfoCard({
  originalMessage,
  onRephrase,
}: {
  originalMessage: string | null;
  onRephrase: (text: string) => void;
}) {
  return (
    <div className="rounded-xl border border-info-soft-foreground/20 bg-info-soft/50 p-4">
      <div className="flex items-start gap-3">
        <Info
          className="mt-0.5 size-4 flex-shrink-0 text-info"
          strokeWidth={1.75}
          aria-hidden="true"
        />
        <div className="min-w-0 flex-1 text-sm">
          <p className="font-medium text-foreground">
            One more step needed.
          </p>
          <p className="mt-1 text-muted-foreground">
            CareFlow doesn't keep conversation memory yet, so please add
            the missing details and send the request as one complete
            message.
          </p>
          {originalMessage && (
            <div className="mt-3 rounded-md border border-border bg-background/60 px-3 py-2 text-xs text-foreground">
              <div className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                Your previous message
              </div>
              <div className="mt-0.5 italic">{originalMessage}</div>
            </div>
          )}
          <button
            type="button"
            disabled={!originalMessage}
            onClick={() => originalMessage && onRephrase(originalMessage)}
            className={cn(
              "mt-3 inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground",
              "hover:bg-muted",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              "disabled:cursor-not-allowed disabled:opacity-60",
            )}
          >
            <PencilLine className="size-3.5" strokeWidth={2} />
            Rephrase and resend
          </button>
        </div>
      </div>
    </div>
  );
}
