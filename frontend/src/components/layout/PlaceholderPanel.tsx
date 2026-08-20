import type { ReactNode } from "react";
import { Construction } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Phase-8.3 building block. Every non-landing page uses this to say —
 * clearly and without pretending — that it's a shell, not a shipped
 * feature. Also documents which future phase will fill it in and the
 * backend contract it will bind to, so the shell doubles as a
 * checklist during Phase 8.4+.
 */
export function PlaceholderPanel({
  route,
  phase,
  endpoint,
  children,
  className,
}: {
  route: string;
  phase: string;
  endpoint?: string;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border border-dashed border-border bg-card/50 p-6",
        className,
      )}
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="inline-flex size-9 flex-shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground"
        >
          <Construction className="size-4.5" strokeWidth={1.75} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-foreground">
            This screen is a Phase-8.3 shell.
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Real functionality arrives in <span className="font-medium text-foreground">{phase}</span>.
          </p>
          <dl className="mt-4 grid grid-cols-1 gap-2 text-xs sm:grid-cols-2">
            <div className="flex flex-col rounded-md border border-border bg-background px-3 py-2">
              <dt className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                Route
              </dt>
              <dd className="mt-0.5 font-mono text-foreground">{route}</dd>
            </div>
            {endpoint && (
              <div className="flex flex-col rounded-md border border-border bg-background px-3 py-2">
                <dt className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                  Backend
                </dt>
                <dd className="mt-0.5 font-mono text-foreground">{endpoint}</dd>
              </div>
            )}
          </dl>
        </div>
      </div>
      {children && <div className="mt-6">{children}</div>}
    </div>
  );
}
