import { Sparkles, User } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Static product preview shown in the landing hero — NOT a live
 * `/chat` call. Two things matter here:
 *
 *   1. The card is unambiguously labelled "Product preview" so no
 *      viewer mistakes the illustrated conversation for a real API
 *      response.
 *   2. The single deliberate ambient motion in the landing lives on
 *      the "Powered by CareFlow AI" chip — a slow heartbeat dot with
 *      an expanding pulse ring. Both animations are gated by
 *      `prefers-reduced-motion` at the CSS level (see `index.css`).
 */
export function HeroPreviewCard() {
  return (
    <div
      className={cn(
        "relative flex h-full flex-col justify-between rounded-2xl border border-border bg-card p-5 sm:p-6",
        "animate-fade-in-up delay-300",
      )}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="inline-flex items-center gap-2 rounded-full bg-primary-soft px-2.5 py-1 text-[11px] font-medium uppercase tracking-widest text-primary-soft-foreground">
          Product preview
        </div>
        <div className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
          Demo · not live
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {/* Patient bubble */}
        <div className="flex items-start gap-3">
          <span
            aria-hidden="true"
            className="mt-0.5 inline-flex size-8 flex-shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground"
          >
            <User className="size-4" strokeWidth={1.75} />
          </span>
          <div className="min-w-0 flex-1">
            <div className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
              Patient
            </div>
            <div className="mt-1 rounded-2xl rounded-tl-md border border-border bg-background/70 px-3.5 py-2.5 text-sm text-foreground">
              Is Dr. Ahmed available today at 5&nbsp;PM?
            </div>
          </div>
        </div>

        {/* AI bubble */}
        <div className="flex items-start gap-3">
          <span
            aria-hidden="true"
            className="mt-0.5 inline-flex size-8 flex-shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground"
          >
            <Sparkles className="size-4" strokeWidth={1.75} />
          </span>
          <div className="min-w-0 flex-1">
            <div className="text-[11px] font-medium uppercase tracking-widest text-primary">
              CareFlow AI
            </div>
            <div className="mt-1 rounded-2xl rounded-tl-md bg-primary-soft px-3.5 py-2.5 text-sm text-primary-soft-foreground">
              Yes — the 5:00&nbsp;PM slot is available.
            </div>
          </div>
        </div>
      </div>

      {/* Ambient "Powered by" chip with heartbeat */}
      <div className="mt-6 flex items-center justify-between border-t border-border pt-4">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span className="relative size-2.5" aria-hidden="true">
            <span className="absolute inset-0 rounded-full bg-status-confirmed/40 animate-pulse-ring" />
            <span className="relative inline-block size-2.5 rounded-full bg-status-confirmed animate-heartbeat" />
          </span>
          <span className="font-medium text-foreground">Powered by CareFlow AI</span>
        </div>
        <div className="text-[11px] uppercase tracking-widest text-muted-foreground">
          Illustrative
        </div>
      </div>
    </div>
  );
}
