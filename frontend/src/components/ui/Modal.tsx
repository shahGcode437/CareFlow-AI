import {
  useEffect,
  useId,
  useRef,
  type KeyboardEvent as ReactKeyboardEvent,
  type ReactNode,
} from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * In-house modal primitive.
 *
 * Deliberately not pulling in `@radix-ui/react-dialog` for one dialog
 * pattern — the wire cost outweighs the reuse. Follows the same
 * accessibility recipe already used by the mobile nav drawer in
 * `components/layout/MobileNav.tsx`:
 *
 *   - `role="dialog"` + `aria-modal="true"` + `aria-labelledby`
 *   - Escape closes; overlay click closes
 *   - Body scroll locked while open
 *   - Focus jumps to the close button on open and restores to the
 *     previously-focused element on close
 *   - A hidden trailing focus guard cycles focus back to the top,
 *     giving a lightweight focus trap without a heavy dependency
 */

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
  /** Prevent close while a mutation is in-flight, etc. */
  dismissible?: boolean;
  className?: string;
}

export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  dismissible = true,
  className,
}: ModalProps) {
  const titleId = useId();
  const descId = useId();
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    previousFocusRef.current =
      (document.activeElement as HTMLElement | null) ?? null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && dismissible) onClose();
    };
    document.addEventListener("keydown", onKey);
    // Focus the close button after the browser has painted.
    queueMicrotask(() => closeButtonRef.current?.focus());
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKey);
      previousFocusRef.current?.focus?.();
    };
  }, [open, dismissible, onClose]);

  if (!open) return null;

  // Lightweight focus recycle: pressing Tab past the last focusable
  // sends focus back to the first, and vice-versa.
  const handleTrap = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "Tab") return;
    const el = containerRef.current;
    if (!el) return;
    const focusable = el.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
    );
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-4"
      onKeyDown={handleTrap}
    >
      <div
        className="absolute inset-0 bg-foreground/40 backdrop-blur-sm animate-fade-in"
        onClick={() => dismissible && onClose()}
        aria-hidden="true"
      />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descId : undefined}
        className={cn(
          "relative z-10 flex max-h-[calc(100dvh-2rem)] w-full flex-col overflow-hidden rounded-t-2xl border border-border bg-card shadow-xl",
          "animate-fade-in-up sm:w-[min(560px,100%)] sm:rounded-2xl",
          className,
        )}
      >
        <header className="flex items-start justify-between gap-3 border-b border-border px-5 py-4 sm:px-6">
          <div className="min-w-0">
            <h2
              id={titleId}
              className="text-base font-semibold tracking-tight text-foreground"
            >
              {title}
            </h2>
            {description && (
              <p id={descId} className="mt-0.5 text-xs text-muted-foreground">
                {description}
              </p>
            )}
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            onClick={onClose}
            disabled={!dismissible}
            aria-label="Close dialog"
            className={cn(
              "inline-flex size-9 flex-shrink-0 items-center justify-center rounded-md text-muted-foreground",
              "hover:bg-muted hover:text-foreground",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              "disabled:cursor-not-allowed disabled:opacity-60",
            )}
          >
            <X className="size-4" strokeWidth={1.75} />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-5 py-5 sm:px-6">{children}</div>

        {footer && (
          <div className="border-t border-border bg-surface px-5 py-4 sm:px-6">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
