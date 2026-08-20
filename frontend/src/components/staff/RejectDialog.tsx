import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Loader2, XCircle } from "lucide-react";
import { Modal } from "@/components/ui/Modal";
import { ApiErrorAlert } from "@/components/feedback/ApiErrorAlert";
import { rejectAppointment } from "@/api/staff";
import type { AppointmentResponse, StaffRejectionRequest } from "@/types/api";
import { cn } from "@/lib/utils";

const REASON_MIN_LENGTH = 3;
const REASON_MAX_LENGTH = 500;

/**
 * Staff rejection dialog — Master Spec API-009.
 *
 * `reason` is required and must be at least 3 characters (matches
 * the backend's Pydantic `min_length: 3` in `AppointmentRejection`).
 * We validate client-side too so an empty reason never reaches the
 * network — no wasted 422 round-trip.
 */
export function RejectDialog({
  open,
  onClose,
  appointment,
  demoStaffId,
}: {
  open: boolean;
  onClose: () => void;
  appointment: AppointmentResponse;
  demoStaffId: string;
}) {
  const [reason, setReason] = useState("");
  const [touched, setTouched] = useState(false);
  const queryClient = useQueryClient();

  const mutation = useMutation<
    AppointmentResponse,
    unknown,
    StaffRejectionRequest
  >({
    mutationFn: (body) => rejectAppointment(appointment.appointment_id, body),
    onSuccess: (updated) => {
      queryClient.setQueryData(
        ["appointment", appointment.appointment_id],
        updated,
      );
      queueMicrotask(() => onClose());
    },
  });

  useEffect(() => {
    if (open) {
      setReason("");
      setTouched(false);
      mutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const trimmed = reason.trim();
  const reasonError =
    touched && trimmed.length < REASON_MIN_LENGTH
      ? `Please enter at least ${REASON_MIN_LENGTH} characters.`
      : touched && trimmed.length > REASON_MAX_LENGTH
        ? `Please keep the reason under ${REASON_MAX_LENGTH} characters.`
        : undefined;
  const canSubmit =
    trimmed.length >= REASON_MIN_LENGTH &&
    trimmed.length <= REASON_MAX_LENGTH &&
    !mutation.isPending;

  const handleConfirm = () => {
    setTouched(true);
    if (!canSubmit) return;
    mutation.mutate({
      reason: trimmed,
      is_staff: true,
      staff_id: demoStaffId,
    });
  };

  const busy = mutation.isPending;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Reject appointment"
      description={`Reject ${appointment.appointment_id} with a reason. Status will move Pending → Rejected.`}
      dismissible={!busy}
    >
      <div className="flex flex-col gap-5">
        <div
          role="note"
          className="flex items-start gap-3 rounded-lg border border-status-rejected/30 bg-status-rejected/5 p-3 text-sm"
        >
          <AlertTriangle
            className="mt-0.5 size-4 flex-shrink-0 text-status-rejected"
            strokeWidth={1.75}
            aria-hidden="true"
          />
          <div>
            <p className="font-medium text-foreground">
              About to Reject this appointment
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {appointment.patient_name} · {appointment.doctor_name} ·{" "}
              {appointment.appointment_date} at {appointment.appointment_time}
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="reject-reason"
            className="text-xs font-medium uppercase tracking-widest text-muted-foreground"
          >
            Reason (required — at least {REASON_MIN_LENGTH} characters)
          </label>
          <textarea
            id="reject-reason"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            onBlur={() => setTouched(true)}
            disabled={busy}
            aria-invalid={!!reasonError}
            aria-describedby={reasonError ? "reject-reason-error" : undefined}
            placeholder="Why is this appointment being rejected?"
            className={cn(
              "min-h-[88px] w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground",
              "placeholder:text-muted-foreground",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              "disabled:cursor-not-allowed disabled:opacity-60",
              reasonError && "border-destructive/60",
            )}
          />
          <div className="flex items-center justify-between">
            {reasonError ? (
              <p id="reject-reason-error" className="text-xs text-destructive">
                {reasonError}
              </p>
            ) : (
              <span />
            )}
            <p className="text-[11px] text-muted-foreground">
              {trimmed.length}/{REASON_MAX_LENGTH}
            </p>
          </div>
        </div>

        {mutation.isError && (
          <ApiErrorAlert
            error={mutation.error}
            onRetry={() => mutation.reset()}
            title="Rejection failed."
          />
        )}

        <p className="text-[11px] text-muted-foreground">
          Sending{" "}
          <code className="rounded bg-muted px-1 py-0.5 font-mono text-foreground">
            is_staff: true, staff_id: "{demoStaffId}"
          </code>{" "}
          — demo placeholder, no real auth.
        </p>

        <div className="flex flex-col gap-2 border-t border-border pt-4 sm:flex-row sm:justify-end">
          <button
            type="button"
            onClick={onClose}
            disabled={busy}
            className={cn(
              "inline-flex min-h-[44px] items-center justify-center rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-foreground",
              "hover:bg-muted",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              "disabled:cursor-not-allowed disabled:opacity-60",
            )}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={busy}
            className={cn(
              "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-md bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground",
              "hover:brightness-95",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              "disabled:cursor-not-allowed disabled:opacity-70",
            )}
          >
            {busy ? (
              <>
                <Loader2 className="size-4 animate-spin" strokeWidth={2} />
                Rejecting…
              </>
            ) : (
              <>
                <XCircle className="size-4" strokeWidth={1.75} />
                Confirm rejection
              </>
            )}
          </button>
        </div>
      </div>
    </Modal>
  );
}
