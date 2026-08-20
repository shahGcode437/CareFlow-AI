import { Link } from "react-router-dom";
import { CalendarCheck2, ExternalLink, PlusCircle } from "lucide-react";
import type { AppointmentResponse, AppointmentStatus } from "@/types/api";
import { formatDate, formatTime } from "@/lib/format";
import { StaffReviewBanner } from "@/components/chat/StaffReviewBanner";
import { cn } from "@/lib/utils";

interface BookingSuccessProps {
  appointment: AppointmentResponse;
  onBookAnother: () => void;
}

/**
 * Full-panel confirmation shown after `POST /appointments` succeeds.
 *
 * Every field displayed is taken straight from the backend's
 * `AppointmentResponse` — nothing is fabricated. The `Pending` status
 * comes from the backend's staff-approval policy; when it does, we
 * surface the standard StaffReviewBanner so the user knows the
 * request isn't yet confirmed.
 */
export function BookingSuccess({
  appointment,
  onBookAnother,
}: BookingSuccessProps) {
  return (
    <div className="animate-fade-in-up rounded-2xl border border-status-confirmed/30 bg-status-confirmed/5 p-6">
      <div className="flex items-start gap-4">
        <span
          aria-hidden="true"
          className="inline-flex size-11 flex-shrink-0 items-center justify-center rounded-full bg-status-confirmed/15 text-status-confirmed"
        >
          <CalendarCheck2 className="size-5" strokeWidth={1.75} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-xs font-medium uppercase tracking-widest text-status-confirmed">
            Request received
          </div>
          <h2 className="mt-1 text-xl font-semibold tracking-tight text-foreground">
            Your appointment request is on file.
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Save the appointment ID below — you can open the full detail
            page anytime to reschedule or cancel.
          </p>
        </div>
        <StatusPill status={appointment.status} />
      </div>

      <dl className="mt-6 grid grid-cols-1 gap-4 rounded-xl border border-border bg-card p-5 text-sm sm:grid-cols-2">
        <Field label="Appointment ID" value={appointment.appointment_id} mono />
        <Field label="Status" value={appointment.status} />
        <Field
          label="Doctor"
          value={`${appointment.doctor_name} · ${appointment.doctor_id}`}
        />
        <Field label="Service" value={appointment.service} />
        <Field label="Date" value={formatDate(appointment.appointment_date)} />
        <Field label="Time" value={formatTime(appointment.appointment_time)} />
        <Field label="Patient" value={appointment.patient_name} />
        <Field label="Phone" value={appointment.patient_phone} mono />
      </dl>

      {appointment.status === "Pending" && <StaffReviewBanner />}

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <Link
          to={`/appointments/${appointment.appointment_id}`}
          className={cn(
            "inline-flex min-h-[44px] items-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground",
            "hover:bg-primary/90",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          )}
        >
          <ExternalLink className="size-4" strokeWidth={1.75} />
          View appointment details
        </Link>
        <button
          type="button"
          onClick={onBookAnother}
          className={cn(
            "inline-flex min-h-[44px] items-center gap-2 rounded-md border border-border bg-card px-5 py-2.5 text-sm font-medium text-foreground",
            "hover:bg-muted",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          )}
        >
          <PlusCircle className="size-4" strokeWidth={1.75} />
          Book another appointment
        </button>
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="min-w-0">
      <dt className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
        {label}
      </dt>
      <dd
        className={
          mono
            ? "mt-0.5 truncate font-mono text-sm text-foreground"
            : "mt-0.5 truncate text-sm text-foreground"
        }
      >
        {value}
      </dd>
    </div>
  );
}

function StatusPill({ status }: { status: AppointmentStatus }) {
  const cls =
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
        "inline-flex flex-shrink-0 items-center rounded-md px-2 py-0.5 text-[11px] font-medium",
        cls,
      )}
    >
      {status}
    </span>
  );
}
