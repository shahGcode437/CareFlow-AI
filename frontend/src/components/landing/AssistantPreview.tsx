import { Link } from "react-router-dom";
import { ArrowRight, Sparkles, User } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Static mid-page preview of the CareFlow assistant. Uses a real,
 * verifiable example (an actual seed doctor, ISO date, 24-hour time)
 * — the same shape any viewer could later type into the live
 * assistant. Refers to the doctor by name ("Dr. Ahmed"), matching
 * what a real patient would type; the backend resolves that to the
 * internal doctor_id itself. NOT wired to `/chat`; the label makes
 * that explicit.
 */
export function AssistantPreview() {
  return (
    <section
      aria-labelledby="landing-assistant-preview"
      className="border-b border-border bg-surface"
    >
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <div className="grid gap-10 md:grid-cols-[2fr_3fr] md:items-center">
          <div className="animate-fade-in-up">
            <div className="text-xs font-medium uppercase tracking-widest text-primary">
              AI Assistant preview
            </div>
            <h2
              id="landing-assistant-preview"
              className="mt-2 text-2xl font-semibold tracking-tight text-foreground sm:text-3xl"
            >
              Ask in plain language.{" "}
              <span className="text-primary">Get a direct answer.</span>
            </h2>
            <p className="mt-3 text-sm text-muted-foreground sm:text-base">
              The Appointment Agent picks the correct tool, calls the
              deterministic service, and reports the outcome faithfully —
              never fabricated, always traceable.
            </p>
            <Link
              to="/assistant"
              className={cn(
                "mt-6 inline-flex items-center gap-1 text-sm font-medium text-primary",
                "hover:text-primary/80",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background rounded",
              )}
            >
              Try the live assistant
              <ArrowRight className="size-4" strokeWidth={2} />
            </Link>
          </div>

          <div
            className={cn(
              "rounded-2xl border border-border bg-card p-5 sm:p-7",
              "animate-fade-in-up delay-150",
            )}
          >
            <div className="flex items-center justify-between">
              <div className="inline-flex items-center gap-2 rounded-full bg-primary-soft px-2.5 py-1 text-[11px] font-medium uppercase tracking-widest text-primary-soft-foreground">
                Product preview
              </div>
              <div className="flex items-center gap-2 text-[11px] uppercase tracking-widest text-muted-foreground">
                <span className="relative size-2" aria-hidden="true">
                  <span className="absolute inset-0 rounded-full bg-status-confirmed/40 animate-pulse-ring" />
                  <span className="relative inline-block size-2 rounded-full bg-status-confirmed animate-heartbeat" />
                </span>
                Powered by CareFlow AI
              </div>
            </div>

            <div className="mt-6 space-y-4">
              {/* User bubble */}
              <div className="flex items-start gap-3">
                <span
                  aria-hidden="true"
                  className="mt-0.5 inline-flex size-9 flex-shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground"
                >
                  <User className="size-4" strokeWidth={1.75} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="text-[11px] font-medium uppercase tracking-widest text-muted-foreground">
                    User
                  </div>
                  <div className="mt-1 rounded-2xl rounded-tl-md border border-border bg-background/70 px-4 py-3 text-sm text-foreground">
                    Is Dr. Ahmed available on 2026-08-16 at 17:00?
                  </div>
                </div>
              </div>

              {/* Assistant bubble */}
              <div className="flex items-start gap-3">
                <span
                  aria-hidden="true"
                  className="mt-0.5 inline-flex size-9 flex-shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground"
                >
                  <Sparkles className="size-4" strokeWidth={1.75} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="text-[11px] font-medium uppercase tracking-widest text-primary">
                    CareFlow
                  </div>
                  <div className="mt-1 rounded-2xl rounded-tl-md bg-primary-soft px-4 py-3 text-sm text-primary-soft-foreground">
                    The requested slot is available.
                  </div>
                  <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background/60 px-2 py-0.5">
                      intent · check_availability
                    </span>
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background/60 px-2 py-0.5">
                      tool · check_availability()
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <p className="mt-6 border-t border-border pt-4 text-[11px] text-muted-foreground">
              Illustrative conversation. The live assistant on{" "}
              <code className="rounded bg-muted px-1 py-0.5 font-mono text-foreground">
                /assistant
              </code>{" "}
              connects to the CareFlow FastAPI backend.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
