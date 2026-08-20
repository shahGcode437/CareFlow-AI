import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

/**
 * Shared page-header block. Used at the top of every non-landing page
 * so titles, descriptions, and per-page actions stay aligned.
 *
 * Accepts an optional eyebrow (small uppercase caption) for context —
 * e.g. "API-002" or "Route /availability". Actions render on the
 * right at md+ and stack below at mobile widths.
 */
export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  className,
}: {
  eyebrow?: string;
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col gap-4 border-b border-border pb-6 md:flex-row md:items-end md:justify-between",
        className,
      )}
    >
      <div className="min-w-0">
        {eyebrow && (
          <div className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
            {eyebrow}
          </div>
        )}
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-foreground md:text-3xl">
          {title}
        </h1>
        {description && (
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex flex-shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}
