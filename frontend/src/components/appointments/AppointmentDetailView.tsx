import { useState } from "react";
import { CalendarClock, CalendarX2, ClipboardList, Clock, User } from "lucide-react";
import type { AppointmentResponse } from "@/types/api";
import { formatDate, formatTime } from "@/lib/format";
import { canMutate, StatusPill } from "./StatusPill";
import { RescheduleDialog } from "./RescheduleDialog";
import { CancelDialog } from "./CancelDialog";
import { cn } from "@/lib/utils";

/**
 * Full-detail read view of a single appointment plus the two patient
 * actions (Reschedule and Cancel). Actions render ONLY when the
 * current status permits mutation (Master Spec §6 "locked states"
 * have no standard mutation).
 */
export function AppointmentDetailView({
  appointment,
}: {
  appointment: AppointmentResponse;
}) {
  const [rescheduleOpen, setRescheduleOpen] = useState(false);
  const [cancelOpen, setCancelOpen] = useState(false);

  const mutable = canMutate(appointment.status);

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      {/* Left: identity + when + notes */}
      <section
        aria-labelledby="appt-detail-heading"
        className="rounded-2xl border border-border bg-card p-6 animate-fade-in-up"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
              Appointment ID
            </div>
            <div
              id="appt-detail-heading"
              className="mt-0.5 truncate font-mono text-lg font-semibold text-foreground"
            >
              {appointment.appointment_id}
            </div>
          </div>
          <StatusPill status={appointment.status} size="md" />
        </div>

        <div className="mt-6 grid gap-6 sm:grid-cols-2">
          <FieldGroup
            icon={User}
            label="Patient"
            primary={appointment.patient_name}
            secondary={appointment.patient_phone}
            secondaryMono
          />
          <FieldGroup
            icon={ClipboardList}
            label="Doctor & service"
            primary={appointment.doctor_name}
            secondary={`${appointment.doctor_id} · ${appointment.service}`}
          />
          <FieldGroup
            icon={CalendarClock}
            label="Date"
            primary={formatDate(appointment.appointment_date)}
          />
          <FieldGroup
            icon={Clock}
            label="Time"
            primary={formatTime(appointment.appointment_time)}
          />
        </div>

        {appointment.notes && (
          <div className="mt-6 rounded-lg border border-border bg-surface p-4">
            <div className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
              Notes
            </div>
            <p className="mt-1 whitespace-pre-line text-sm text-foreground">
              {appointment.notes}
            </p>
          </div>
        )}
      </section>

      {/* Right: actions + audit */}
      <aside className="flex flex-col gap-4">
        <div className="rounded-2xl border border-border bg-card p-6 animate-fade-in-up">
          <h2 className="text-sm font-semibold tracking-tight text-foreground">
            Actions
          </h2>
          {mutable ? (
            <>
              <p className="mt-1 text-xs text-muted-foreground">
                You can reschedule or cancel while the appointment is{" "}
                <span className="font-medium text-foreground">
                  {appointment.status}
                </span>
                .
              </p>
              <div className="mt-4 flex flex-col gap-2">
                <button
                  type="button"
                  onClick={() => setRescheduleOpen(true)}
                  className={cn(
                    "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground",
                    "hover:bg-primary/90",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  )}
                >
                  <CalendarClock className="size-4" strokeWidth={1.75} />
                  Reschedule
                </button>
                <button
                  type="button"
                  onClick={() => setCancelOpen(true)}
                  className={cn(
                    "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-foreground",
                    "hover:bg-muted",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  )}
                >
                  <CalendarX2 className="size-4" strokeWidth={1.75} />
                  Cancel appointment
                </button>
              </div>
            </>
          ) : (
            <p className="mt-3 text-sm text-muted-foreground">
              This appointment is{" "}
              <span className="font-medium text-foreground">
                {appointment.status}
              </span>{" "}
              — no further changes are allowed. Contact the clinic if you
              believe this is wrong.
            </p>
          )}
        </div>

        <div className="rounded-2xl border border-border bg-card p-6">
          <h2 className="text-sm font-semibold tracking-tight text-foreground">
            Record
          </h2>
          <dl className="mt-3 grid grid-cols-1 gap-3 text-sm">
            <Field
              label="Created"
              value={formatTimestamp(appointment.created_at)}
            />
            <Field
              label="Last updated"
              value={formatTimestamp(appointment.updated_at)}
            />
          </dl>
        </div>
      </aside>

      <RescheduleDialog
        open={rescheduleOpen}
        onClose={() => setRescheduleOpen(false)}
        appointment={appointment}
      />
      <CancelDialog
        open={cancelOpen}
        onClose={() => setCancelOpen(false)}
        appointment={appointment}
      />
    </div>
  );
}

function FieldGroup({
  icon: Icon,
  label,
  primary,
  secondary,
  secondaryMono,
}: {
  icon: typeof User;
  label: string;
  primary: string;
  secondary?: string;
  secondaryMono?: boolean;
}) {
  return (
    <div className="flex items-start gap-3">
      <span
        aria-hidden="true"
        className="mt-0.5 inline-flex size-9 flex-shrink-0 items-center justify-center rounded-md bg-primary-soft text-primary"
      >
        <Icon className="size-4" strokeWidth={1.75} />
      </span>
      <div className="min-w-0">
        <div className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
          {label}
        </div>
        <div className="mt-0.5 truncate text-sm font-medium text-foreground">
          {primary}
        </div>
        {secondary && (
          <div
            className={cn(
              "mt-0.5 truncate text-xs text-muted-foreground",
              secondaryMono && "font-mono",
            )}
          >
            {secondary}
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-0.5 truncate text-sm text-foreground">{value}</dd>
    </div>
  );
}

/**
 * Backend returns naive ISO timestamps like "2026-08-16T10:00:00". Show
 * them in the user's locale without pretending to know a timezone the
 * backend didn't include.
 */
function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
