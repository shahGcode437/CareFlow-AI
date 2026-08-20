import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Small, quiet spinner. The visible label doubles as the accessible
 * name — screen readers announce it, and sighted users see whatever
 * context you pass in `label`. If you want the spinner without any
 * text (e.g. inside a button), pass `label=""` — an `aria-label` is
 * still applied so the control isn't silent.
 */
export function LoadingSpinner({
  label = "Loading…",
  className,
  iconClassName,
}: {
  label?: string;
  className?: string;
  iconClassName?: string;
}) {
  return (
    <span
      role="status"
      aria-live="polite"
      aria-label={label || "Loading"}
      className={cn("inline-flex items-center gap-2 text-muted-foreground", className)}
    >
      <Loader2
        className={cn("size-4 animate-spin", iconClassName)}
        strokeWidth={2}
        aria-hidden="true"
      />
      {label && <span className="text-sm">{label}</span>}
    </span>
  );
}
