import type { AppointmentStatus } from "@/types/api";
import { cn } from "@/lib/utils";

/**
 * Semantic status badge shared across every appointment view. Colors
 * come from the design-token palette so they carry meaning at a glance
 * without relying on the label text alone.
 */
export function StatusPill({
  status,
  size = "sm",
}: {
  status: AppointmentStatus;
  size?: "sm" | "md";
}) {
  const tone =
    status === "Pending"
      ? "bg-status-pending text-status-pending-foreground"
      : status === "Confirmed"
        ? "bg-status-confirmed text-status-confirmed-foreground"
        : status === "Cancelled"
          ? "bg-status-cancelled text-status-cancelled-foreground"
          : status === "Rejected"
            ? "bg-status-rejected text-status-rejected-foreground"
            : status === "Completed"
              ? "bg-status-completed text-status-completed-foreground"
              : "bg-status-noshow text-status-noshow-foreground";

  return (
    <span
      className={cn(
        "inline-flex flex-shrink-0 items-center rounded-md font-medium",
        size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs",
        tone,
      )}
    >
      {status}
    </span>
  );
}

/**
 * Master Spec §6 — "locked" states have no standard mutation.
 * Reschedule/Cancel are only meaningful for Pending or Confirmed.
 */
export function canMutate(status: AppointmentStatus): boolean {
  return status === "Pending" || status === "Confirmed";
}
