import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CalendarSearch, ClipboardCheck, Loader2 } from "lucide-react";
import { Modal } from "@/components/ui/Modal";
import { DateTimeFields } from "@/components/booking/DateTimeFields";
import { AvailabilityStatus } from "@/components/booking/AvailabilityStatus";
import { ApiErrorAlert } from "@/components/feedback/ApiErrorAlert";
import { checkAvailability, updateAppointment } from "@/api/appointments";
import type {
  AppointmentResponse,
  AppointmentUpdate,
  AvailabilityRequest,
  AvailabilityResponse,
} from "@/types/api";
import { trimSeconds } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Reschedule flow — pre-flight availability check, then PATCH.
 *
 *   1. User picks a new date + time (existing values pre-fill).
 *   2. "Check availability" hits `POST /appointments/check-availability`
 *      with the appointment's existing doctor + service and the newly
 *      chosen date/time.
 *   3. If unavailable, the assistant-handoff card renders and PATCH
 *      is not offered. If available, "Confirm reschedule" appears.
 *   4. Confirm sends a PATCH with ONLY the date/time fields — the
 *      contract intentionally accepts partial updates
 *      (`AppointmentUpdate` — all fields optional).
 *   5. On success, the appointment cache is updated in place and the
 *      dialog closes.
 */
export function RescheduleDialog({
  open,
  onClose,
  appointment,
}: {
  open: boolean;
  onClose: () => void;
  appointment: AppointmentResponse;
}) {
  const [date, setDate] = useState(appointment.appointment_date);
  const [time, setTime] = useState(trimSeconds(appointment.appointment_time));
  const [touched, setTouched] = useState(false);

  const queryClient = useQueryClient();

  const checkMutation = useMutation<
    AvailabilityResponse,
    unknown,
    AvailabilityRequest
  >({
    mutationFn: (body) => checkAvailability(body),
  });

  const rescheduleMutation = useMutation<
    AppointmentResponse,
    unknown,
    AppointmentUpdate
  >({
    mutationFn: (body) => updateAppointment(appointment.appointment_id, body),
    onSuccess: (updated) => {
      queryClient.setQueryData(
        ["appointment", appointment.appointment_id],
        updated,
      );
      // Close the dialog after the parent has a chance to re-render.
      queueMicrotask(() => onClose());
    },
  });

  // Reset both mutations when the dialog reopens so a previous run
  // doesn't leak stale success/error state.
  useEffect(() => {
    if (open) {
      setDate(appointment.appointment_date);
      setTime(trimSeconds(appointment.appointment_time));
      setTouched(false);
      checkMutation.reset();
      rescheduleMutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // Any date/time change invalidates a previous availability result.
  useEffect(() => {
    if (checkMutation.status !== "idle") checkMutation.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [date, time]);

  const missing = { date: !date, time: !time };
  const hasErrors = missing.date || missing.time;
  const unchanged =
    date === appointment.appointment_date &&
    time === trimSeconds(appointment.appointment_time);
  const isAvailable = checkMutation.data?.available === true;
  const busy = checkMutation.isPending || rescheduleMutation.isPending;

  const handleCheck = () => {
    setTouched(true);
    if (hasErrors || unchanged) return;
    checkMutation.mutate({
      doctor_id: appointment.doctor_id,
      appointment_date: date,
      appointment_time: time,
      service: appointment.service || null,
    });
  };

  const handleConfirm = () => {
    rescheduleMutation.mutate({
      appointment_date: date,
      appointment_time: time,
    });
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Reschedule appointment"
      description={`Pick a new date and time for ${appointment.appointment_id}. CareFlow will confirm availability before rescheduling.`}
      dismissible={!busy}
    >
      <div className="flex flex-col gap-5">
        <div className="rounded-lg border border-border bg-surface p-3 text-xs text-muted-foreground">
          Currently scheduled for{" "}
          <span className="font-medium text-foreground">
            {appointment.appointment_date} · {trimSeconds(appointment.appointment_time)}
          </span>{" "}
          with{" "}
          <span className="font-medium text-foreground">
            {appointment.doctor_name}
          </span>
          .
        </div>

        <DateTimeFields
          dateId={`reschedule-${appointment.appointment_id}-date`}
          timeId={`reschedule-${appointment.appointment_id}-time`}
          doctorId={appointment.doctor_id}
          date={date}
          time={time}
          onDateChange={setDate}
          onTimeChange={setTime}
          dateError={touched && missing.date ? "Please pick a date" : undefined}
          timeError={touched && missing.time ? "Please pick a time" : undefined}
          disabled={busy}
        />

        {unchanged && touched && (
          <p className="text-xs text-muted-foreground">
            Pick a different date or time to reschedule.
          </p>
        )}

        {checkMutation.isError && (
          <ApiErrorAlert
            error={checkMutation.error}
            onRetry={() => checkMutation.reset()}
            title="Availability check failed."
          />
        )}

        {checkMutation.isSuccess && (
          <AvailabilityStatus data={checkMutation.data} showAssistantHandoff={!isAvailable} />
        )}

        {rescheduleMutation.isError && (
          <ApiErrorAlert
            error={rescheduleMutation.error}
            onRetry={() => rescheduleMutation.reset()}
            title="Reschedule failed."
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
            Keep original
          </button>

          {!isAvailable && (
            <button
              type="button"
              onClick={handleCheck}
              disabled={busy || hasErrors || unchanged}
              className={cn(
                "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground",
                "hover:bg-primary/90",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                "disabled:cursor-not-allowed disabled:opacity-70",
              )}
            >
              {checkMutation.isPending ? (
                <>
                  <Loader2 className="size-4 animate-spin" strokeWidth={2} />
                  Checking…
                </>
              ) : (
                <>
                  <CalendarSearch className="size-4" strokeWidth={1.75} />
                  Check availability
                </>
              )}
            </button>
          )}

          {isAvailable && (
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
              {rescheduleMutation.isPending ? (
                <>
                  <Loader2 className="size-4 animate-spin" strokeWidth={2} />
                  Rescheduling…
                </>
              ) : (
                <>
                  <ClipboardCheck className="size-4" strokeWidth={1.75} />
                  Confirm reschedule
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </Modal>
  );
}
