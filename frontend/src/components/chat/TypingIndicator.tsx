import { cn } from "@/lib/utils";

/**
 * Minimal "assistant is thinking" indicator. Three dots that pulse in
 * sequence via CSS delays — no runtime timers, gated by
 * `prefers-reduced-motion` at the utility level in `index.css`.
 */
export function TypingIndicator({ className }: { className?: string }) {
  return (
    <div
      role="status"
      aria-label="CareFlow is thinking"
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-2",
        className,
      )}
    >
      <span
        className="inline-block size-1.5 rounded-full bg-primary animate-heartbeat"
        aria-hidden="true"
      />
      <span
        className="inline-block size-1.5 rounded-full bg-primary animate-heartbeat delay-150"
        aria-hidden="true"
      />
      <span
        className="inline-block size-1.5 rounded-full bg-primary animate-heartbeat delay-300"
        aria-hidden="true"
      />
      <span className="ml-1 text-xs text-muted-foreground">Thinking…</span>
    </div>
  );
}
