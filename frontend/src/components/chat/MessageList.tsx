import { useEffect, useRef, type ReactNode } from "react";
import { cn } from "@/lib/utils";

const NEAR_BOTTOM_PX = 96;

/**
 * Scrollable message region with a "stay-anchored-to-bottom" behavior
 * that follows the standard chat rule: auto-scroll only if the user
 * was already at the bottom (or close to it). If they've scrolled up
 * to re-read, we don't yank them back.
 *
 * Semantic wrapper: `role="log"` + `aria-live="polite"` so screen
 * readers announce new content without interrupting.
 */
export function MessageList({
  children,
  scrollTrigger,
  className,
}: {
  children: ReactNode;
  /** Any changing value (e.g. `messages.length`) forces the effect. */
  scrollTrigger: number;
  className?: string;
}) {
  const scrollerRef = useRef<HTMLDivElement | null>(null);
  const wasAtBottomRef = useRef(true);

  // Track whether the user is (approximately) at the bottom BEFORE the
  // new content renders.
  useEffect(() => {
    const el = scrollerRef.current;
    if (!el) return;
    const distanceFromBottom =
      el.scrollHeight - (el.scrollTop + el.clientHeight);
    wasAtBottomRef.current = distanceFromBottom <= NEAR_BOTTOM_PX;
  }, [scrollTrigger]);

  useEffect(() => {
    const el = scrollerRef.current;
    if (!el) return;
    if (wasAtBottomRef.current) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, [scrollTrigger]);

  return (
    <div
      ref={scrollerRef}
      role="log"
      aria-live="polite"
      aria-label="Conversation with CareFlow AI"
      className={cn(
        "flex-1 space-y-6 overflow-y-auto px-4 py-6 sm:px-6",
        className,
      )}
    >
      {children}
    </div>
  );
}
