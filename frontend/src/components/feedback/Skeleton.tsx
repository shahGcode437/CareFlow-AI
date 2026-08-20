import { cn } from "@/lib/utils";

/**
 * Content-shape placeholder for lists and cards. Purely decorative —
 * `aria-hidden` keeps it silent to assistive tech; wrap a real
 * `role="status"` region around it if you need an announcement.
 */
export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      aria-hidden="true"
      className={cn(
        "animate-pulse rounded-md bg-muted",
        className,
      )}
    />
  );
}
