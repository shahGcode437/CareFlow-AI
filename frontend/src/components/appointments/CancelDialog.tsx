import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, CalendarX2, Loader2 } from "lucide-react";
import { Modal } from "@/components/ui/Modal";
import { ApiErrorAlert } from "@/components/feedback/ApiErrorAlert";
import { cancelAppointment } from "@/api/appointments";
import type { AppointmentCancelRequest, AppointmentResponse } from "@/types/api";
import { cn } from "@/lib/utils";

/**
 * Cancellation flow. The dialog is itself the confirmation — the user
 * types (optional) reason and clicks "Cancel appointment". No
 * additional confirmation prompt is chained on top; the destructive
 * copy makes the outcome unambiguous, and the appointment status
 * transitions to `Cancelled` (never physically deleted, per Master
 * Spec §7 / repository README).
 */
export function CancelDialog({
  open,
  onClose,
  appointment,
}: {
  open: boolean;
  onClose: () => void;
  appointment: AppointmentResponse;
}) {
  const [reason, setReason] = useState("");
  const queryClient = useQueryClient();

  const mutation = useMutation<
    AppointmentResponse,
    unknown,
    AppointmentCancelRequest
  >({
    mutationFn: (body) => cancelAppointment(appointment.appointment_id, body),
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
      mutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const handleConfirm = () => {
    const trimmed = reason.trim();
    mutation.mutate({ reason: trimmed.length > 0 ? trimmed : null });
  };

  const busy = mutation.isPending;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Cancel appointment"
      description={`Cancelling ${appointment.appointment_id} sets the status to Cancelled and keeps the record on file — nothing is deleted.`}
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
              This will free the slot immediately.
            </p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              To keep the appointment, close this dialog and no changes
              are made.
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="cancel-reason"
            className="text-xs font-medium uppercase tracking-widest text-muted-foreground"
          >
            Reason (optional)
          </label>
          <textarea
            id="cancel-reason"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            disabled={busy}
            placeholder="Anything the clinic should know."
            className={cn(
              "min-h-[88px] w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground",
              "placeholder:text-muted-foreground",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              "disabled:cursor-not-allowed disabled:opacity-60",
            )}
          />
        </div>

        {mutation.isError && (
          <ApiErrorAlert
            error={mutation.error}
            onRetry={() => mutation.reset()}
            title="Cancellation failed."
          />
        )}

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
            Keep appointment
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
                Cancelling…
              </>
            ) : (
              <>
                <CalendarX2 className="size-4" strokeWidth={1.75} />
                Cancel appointment
              </>
            )}
          </button>
        </div>
      </div>
    </Modal>
  );
}
