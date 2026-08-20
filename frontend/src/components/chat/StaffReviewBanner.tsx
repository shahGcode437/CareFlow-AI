import { ShieldAlert } from "lucide-react";

/**
 * Subtle clinical amber notice — shown under an assistant reply when
 * the backend flagged `requires_staff_review === true`. Never claims
 * that staff has approved anything; only reports the state the backend
 * actually returned.
 */
export function StaffReviewBanner() {
  return (
    <div
      role="note"
      className="mt-2 flex items-start gap-2 rounded-md border border-status-pending/40 bg-status-pending/10 px-3 py-2 text-xs"
    >
      <ShieldAlert
        className="mt-0.5 size-3.5 flex-shrink-0 text-status-pending"
        strokeWidth={1.75}
        aria-hidden="true"
      />
      <span className="text-foreground">
        Your request has been sent for clinic staff review.
      </span>
    </div>
  );
}
