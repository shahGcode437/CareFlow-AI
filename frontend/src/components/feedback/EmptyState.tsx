import type { ReactNode } from "react";
import { Inbox, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * "There's nothing here yet" region. Neutral tone — never treats
 * emptiness as an error. Optional `action` slot for a primary next
 * step (e.g. "Start a chat", "Book an appointment").
 */
export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
}: {
  icon?: LucideIcon;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center rounded-lg border border-dashed border-border bg-card/50 px-6 py-12 text-center",
        className,
      )}
    >
      <span
        aria-hidden="true"
        className="mb-4 inline-flex size-11 items-center justify-center rounded-full bg-muted text-muted-foreground"
      >
        <Icon className="size-5" strokeWidth={1.75} />
      </span>
      <h2 className="text-base font-semibold tracking-tight text-foreground">
        {title}
      </h2>
      {description && (
        <p className="mt-1 max-w-sm text-sm text-muted-foreground">
          {description}
        </p>
      )}
      {action && <div className="mt-5 flex items-center gap-2">{action}</div>}
    </div>
  );
}
