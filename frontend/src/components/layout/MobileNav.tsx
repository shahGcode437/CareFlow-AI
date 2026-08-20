import { useEffect, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { NAV_ITEMS, isActivePath } from "@/config/routes";
import { cn } from "@/lib/utils";

/**
 * Mobile navigation drawer. Hidden at `md` and above; opens as a
 * full-height slide-in panel from the right on smaller viewports.
 *
 * Accessibility notes:
 *   - Trigger and close buttons are ≥ 44 × 44 px.
 *   - The drawer is a `role="dialog"` with `aria-modal="true"`.
 *   - Escape closes; clicking the scrim closes; body scroll is locked.
 *   - Initial focus moves to the close button when the drawer opens,
 *     so the sighted-first-tab and screen-reader-first-announcement
 *     both land on something predictable.
 *   - Route changes close the drawer, so the user isn't stranded
 *     after tapping a link.
 */
export function MobileNav() {
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const triggerButtonRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    closeButtonRef.current?.focus();
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKey);
      triggerButtonRef.current?.focus();
    };
  }, [open]);

  return (
    <>
      <button
        ref={triggerButtonRef}
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open navigation menu"
        aria-expanded={open}
        aria-controls="mobile-nav-drawer"
        className={cn(
          "inline-flex size-11 items-center justify-center rounded-md border border-transparent md:hidden",
          "text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        )}
      >
        <Menu className="size-5" strokeWidth={1.75} />
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 md:hidden"
          role="presentation"
          onClick={() => setOpen(false)}
        >
          <div className="absolute inset-0 bg-foreground/40 backdrop-blur-sm transition-opacity" />
          <div
            id="mobile-nav-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Navigation"
            onClick={(e) => e.stopPropagation()}
            className={cn(
              "absolute inset-y-0 right-0 flex w-[86%] max-w-sm flex-col",
              "border-l border-border bg-card text-card-foreground shadow-xl",
              // safe area on iOS so the panel doesn't collide with the
              // dynamic bottom bar
              "pb-[env(safe-area-inset-bottom)]",
            )}
          >
            <div className="flex h-16 items-center justify-between border-b border-border px-4">
              <span className="text-sm font-semibold tracking-tight">
                Navigate
              </span>
              <button
                ref={closeButtonRef}
                type="button"
                onClick={() => setOpen(false)}
                aria-label="Close navigation menu"
                className={cn(
                  "inline-flex size-11 items-center justify-center rounded-md",
                  "text-muted-foreground hover:bg-muted hover:text-foreground",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                )}
              >
                <X className="size-5" strokeWidth={1.75} />
              </button>
            </div>

            <nav
              aria-label="Primary (mobile)"
              className="flex-1 overflow-y-auto p-3"
            >
              <ul className="flex flex-col gap-1">
                {NAV_ITEMS.map((item) => {
                  const active = isActivePath(pathname, item.path);
                  return (
                    <li key={item.path}>
                      <Link
                        to={item.path}
                        aria-current={active ? "page" : undefined}
                        className={cn(
                          "flex items-start gap-3 rounded-md px-3 py-3",
                          "min-h-[44px]",
                          active
                            ? "bg-accent text-accent-foreground"
                            : "text-foreground hover:bg-muted",
                          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                        )}
                      >
                        <item.icon
                          className="mt-0.5 size-5 text-muted-foreground"
                          strokeWidth={1.75}
                        />
                        <span className="flex flex-col">
                          <span className="text-sm font-medium">
                            {item.label}
                          </span>
                          <span className="mt-0.5 text-xs text-muted-foreground">
                            {item.description}
                          </span>
                        </span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </nav>
          </div>
        </div>
      )}
    </>
  );
}
