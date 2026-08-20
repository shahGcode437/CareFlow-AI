import type { ReactNode } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { ApiError } from "@/lib/apiClient";
import { cn } from "@/lib/utils";

/**
 * Inline alert that renders any `ApiError` (or fallback `Error`) in
 * one consistent shape. Shows:
 *   - a short, safe message (never raw stack traces)
 *   - the backend `X-Request-ID` when we have one, so a support
 *     conversation can correlate what the server saw
 *   - the list of Pydantic `fieldErrors` when this was a 422
 *   - an optional Retry button
 *
 * Deliberately does NOT render `error.details` — those can contain
 * unfiltered server payloads and shouldn't reach the user.
 */
export function ApiErrorAlert({
  error,
  title,
  onRetry,
  children,
  className,
}: {
  error: unknown;
  title?: string;
  onRetry?: () => void;
  children?: ReactNode;
  className?: string;
}) {
  const parsed = normalize(error);

  return (
    <div
      role="alert"
      aria-live="polite"
      className={cn(
        "flex items-start gap-3 rounded-lg border border-destructive/25 bg-destructive/5 p-4",
        className,
      )}
    >
      <AlertCircle
        className="mt-0.5 size-5 flex-shrink-0 text-destructive"
        strokeWidth={1.75}
        aria-hidden="true"
      />
      <div className="min-w-0 flex-1 text-sm">
        <p className="font-medium text-foreground">{title ?? parsed.headline}</p>
        <p className="mt-0.5 text-muted-foreground">{parsed.message}</p>

        {parsed.fieldErrors && parsed.fieldErrors.length > 0 && (
          <ul className="mt-3 list-inside list-disc space-y-0.5 text-muted-foreground">
            {parsed.fieldErrors.map((fe, i) => (
              <li key={`${fe.path}-${i}`}>
                <span className="font-mono text-xs text-foreground">
                  {fe.path}
                </span>{" "}
                — {fe.message}
              </li>
            ))}
          </ul>
        )}

        {parsed.requestId && (
          <p className="mt-3 text-xs text-muted-foreground">
            Request ID:{" "}
            <span className="font-mono text-foreground">{parsed.requestId}</span>
          </p>
        )}

        {(onRetry || children) && (
          <div className="mt-3 flex items-center gap-2">
            {onRetry && (
              <button
                type="button"
                onClick={onRetry}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground",
                  "hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                )}
              >
                <RefreshCw className="size-3.5" strokeWidth={2} />
                Try again
              </button>
            )}
            {children}
          </div>
        )}
      </div>
    </div>
  );
}

interface NormalizedError {
  headline: string;
  message: string;
  requestId?: string;
  fieldErrors?: { path: string; message: string }[];
}

function normalize(error: unknown): NormalizedError {
  if (error instanceof ApiError) {
    const headline =
      error.kind === "network"
        ? "Couldn't reach the backend."
        : error.kind === "timeout"
          ? "The request timed out."
          : error.kind === "validation"
            ? "Some fields need attention."
            : error.kind === "business"
              ? "That action couldn't be completed."
              : "Something went wrong.";
    return {
      headline,
      message: error.message,
      requestId: error.requestId,
      fieldErrors: error.fieldErrors?.map((fe) => ({
        path: fe.path,
        message: fe.message,
      })),
    };
  }
  if (error instanceof Error) {
    return { headline: "Something went wrong.", message: error.message };
  }
  return {
    headline: "Something went wrong.",
    message: "An unexpected error occurred. Please try again.",
  };
}
