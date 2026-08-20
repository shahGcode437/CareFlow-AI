import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Concrete starter prompts — every one is a real capability against
 * the current backend, and every date/time in the copy actually
 * exists in the seed workbook (Dr. Ahmed = DOC-001, APT-001,
 * 2026-08-16).
 *
 * Doctor references use the human-readable name rather than the
 * internal "DOC-001" id — patients shouldn't need to know an
 * identifier to ask a question. The backend resolves "Dr. Ahmed" (or
 * bare "Ahmed") to the stable doctor_id itself (Phase 9.6); a literal
 * "DOC-001" still works too, it's just not what we show as an example.
 *
 * The rule-based provider (the default) can extract these tokens
 * verbatim; the Groq provider handles them at least as well. So
 * suggested prompts work regardless of which LLM is configured.
 */

interface SuggestedPromptsProps {
  onSelect: (prompt: string) => void;
  disabled?: boolean;
  className?: string;
}

const PROMPTS: { label: string; message: string }[] = [
  {
    label: "Check a specific slot",
    message: "Is Dr. Ahmed available on 2026-08-16 at 17:30?",
  },
  {
    label: "Look up an appointment",
    message: "Look up appointment APT-001",
  },
  {
    label: "Find alternative slots",
    message:
      "Find alternative slots with Dr. Ahmed on 2026-08-16 at 17:00",
  },
  {
    label: "Cancel a request",
    message: "Cancel appointment APT-001",
  },
];

export function SuggestedPrompts({
  onSelect,
  disabled,
  className,
}: SuggestedPromptsProps) {
  return (
    <div className={cn("grid gap-2 sm:grid-cols-2", className)}>
      {PROMPTS.map((p) => (
        <button
          key={p.message}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(p.message)}
          className={cn(
            "group flex flex-col rounded-lg border border-border bg-card px-4 py-3 text-left",
            "min-h-[64px] transition-colors hover:border-primary/40 hover:bg-accent/30",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
            "disabled:cursor-not-allowed disabled:opacity-60",
          )}
        >
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-muted-foreground">
            <Sparkles
              className="size-3 text-primary"
              strokeWidth={2}
              aria-hidden="true"
            />
            {p.label}
          </div>
          <div className="mt-1 text-sm text-foreground">{p.message}</div>
        </button>
      ))}
    </div>
  );
}
