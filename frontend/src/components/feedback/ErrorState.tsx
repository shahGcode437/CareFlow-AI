import type { ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Full-region error surface — the "something went wrong on this
 * screen" block. Distinct from `<ApiErrorAlert/>`, which is inline
 * and knows about the `ApiError` shape.
 */
export function ErrorState({
  title = "Something went wrong.",
  description,
  action,
  className,
}: {
  title?: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-center rounded-lg border border-destructive/25 bg-destructive/5 px-6 py-10 text-center",
        className,
      )}
    >
      <span
        aria-hidden="true"
        className="mb-4 inline-flex size-11 items-center justify-center rounded-full bg-destructive/10 text-destructive"
      >
        <AlertTriangle className="size-5" strokeWidth={1.75} />
      </span>
      <h2 className="text-base font-semibold tracking-tight text-foreground">
        {title}
      </h2>
      {description && (
        <p className="mt-1 max-w-md text-sm text-muted-foreground">
          {description}
        </p>
      )}
      {action && <div className="mt-5 flex items-center gap-2">{action}</div>}
    </div>
  );
}
