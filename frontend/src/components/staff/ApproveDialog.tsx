import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Loader2 } from "lucide-react";
import { Modal } from "@/components/ui/Modal";
import { ApiErrorAlert } from "@/components/feedback/ApiErrorAlert";
import { approveAppointment } from "@/api/staff";
import type { AppointmentResponse, StaffApprovalRequest } from "@/types/api";
import { cn } from "@/lib/utils";

/**
 * Staff approval dialog — Master Spec API-008.
 *
 * `is_staff` is a **demo placeholder** on the wire (no real auth
 * boundary on the backend yet). This dialog collects an optional
 * note, sends the mutation, and updates the shared appointment cache
 * on success so the parent detail view reflects the new Confirmed
 * status without a refetch.
 */
export function ApproveDialog({
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
  const [notes, setNotes] = useState("");
  const queryClient = useQueryClient();

  const mutation = useMutation<
    AppointmentResponse,
    unknown,
    StaffApprovalRequest
  >({
    mutationFn: (body) => approveAppointment(appointment.appointment_id, body),
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
      setNotes("");
      mutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const handleConfirm = () => {
    const trimmed = notes.trim();
    mutation.mutate({
      is_staff: true,
      staff_id: demoStaffId,
      notes: trimmed.length > 0 ? trimmed : null,
    });
  };

  const busy = mutation.isPending;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Approve appointment"
      description={`Confirm ${appointment.appointment_id} for ${appointment.patient_name}. Status will move Pending → Confirmed.`}
      dismissible={!busy}
    >
      <div className="flex flex-col gap-5">
        <div className="rounded-lg border border-status-confirmed/30 bg-status-confirmed/5 p-3 text-sm">
          <p className="font-medium text-foreground">
            About to Confirm this appointment
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {appointment.doctor_name} · {appointment.service} ·{" "}
            {appointment.appointment_date} at {appointment.appointment_time}
          </p>
        </div>

        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="approve-notes"
            className="text-xs font-medium uppercase tracking-widest text-muted-foreground"
          >
            Staff notes (optional)
          </label>
          <textarea
            id="approve-notes"
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            disabled={busy}
            placeholder="Anything the clinic should keep on record."
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
            title="Approval failed."
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
              "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-md bg-status-confirmed px-4 py-2 text-sm font-medium text-status-confirmed-foreground",
              "hover:brightness-95",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              "disabled:cursor-not-allowed disabled:opacity-70",
            )}
          >
            {busy ? (
              <>
                <Loader2 className="size-4 animate-spin" strokeWidth={2} />
                Approving…
              </>
            ) : (
              <>
                <CheckCircle2 className="size-4" strokeWidth={1.75} />
                Confirm approval
              </>
            )}
          </button>
        </div>
      </div>
    </Modal>
  );
}
