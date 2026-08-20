import { Link } from "react-router-dom";
import { ArrowUpRight, CalendarDays } from "lucide-react";
import type { AppointmentResponse, AppointmentStatus } from "@/types/api";
import { formatDate, formatTime } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * Used for every intent that resolves to an `AppointmentResponse` —
 * `create_appointment`, `get_appointment`, `update_appointment`,
 * `cancel_appointment`, `approve_appointment`, `reject_appointment`.
 * The status pill uses the semantic status tokens from the design
 * system so the meaning carries even at a glance.
 */
export function AppointmentResultCard({
  data,
}: {
  data: AppointmentResponse;
}) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-muted-foreground">
          <CalendarDays className="size-3.5" strokeWidth={2} />
          Appointment · <span className="font-mono">{data.appointment_id}</span>
        </div>
        <StatusPill status={data.status} />
      </div>

      <dl className="mt-3 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
        <Field label="Patient" value={data.patient_name} />
        <Field label="Doctor" value={`${data.doctor_name} · ${data.doctor_id}`} />
        <Field label="Service" value={data.service} />
        <Field
          label="When"
          value={`${formatDate(data.appointment_date)} · ${formatTime(data.appointment_time)}`}
        />
      </dl>

      {data.notes && (
        <p className="mt-3 rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Notes:</span>{" "}
          {data.notes}
        </p>
      )}

      <div className="mt-3 flex items-center justify-end">
        <Link
          to={`/appointments/${data.appointment_id}`}
          className={cn(
            "inline-flex items-center gap-1 text-xs font-medium text-primary hover:text-primary/80",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background rounded",
          )}
        >
          Open full detail
          <ArrowUpRight className="size-3.5" strokeWidth={2} />
        </Link>
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
        "inline-flex items-center rounded-md px-2 py-0.5 text-[11px] font-medium",
        cls,
      )}
    >
      {status}
    </span>
  );
}
