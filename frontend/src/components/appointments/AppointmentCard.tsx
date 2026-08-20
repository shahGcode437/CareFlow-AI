import { Link } from "react-router-dom";
import { ArrowUpRight, CalendarDays } from "lucide-react";
import type { AppointmentResponse } from "@/types/api";
import { formatDate, formatTime } from "@/lib/format";
import { StatusPill } from "./StatusPill";
import { cn } from "@/lib/utils";

/**
 * Compact summary card — used by the /appointments lookup after a
 * successful `GET /appointments/{id}`. Everything visible is taken
 * directly from the backend response; nothing is derived or inferred.
 */
export function AppointmentCard({
  appointment,
  className,
}: {
  appointment: AppointmentResponse;
  className?: string;
}) {
  return (
    <article
      className={cn(
        "flex flex-col gap-4 rounded-2xl border border-border bg-card p-5 sm:p-6 animate-fade-in-up hover-lift",
        className,
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-muted-foreground">
            <CalendarDays className="size-3.5" strokeWidth={2} />
            Appointment ·{" "}
            <span className="font-mono">{appointment.appointment_id}</span>
          </div>
          <h3 className="mt-1 truncate text-lg font-semibold tracking-tight text-foreground">
            {appointment.patient_name}
          </h3>
          <p className="text-sm text-muted-foreground">
            {appointment.doctor_name} · {appointment.service}
          </p>
        </div>
        <StatusPill status={appointment.status} />
      </div>

      <dl className="grid grid-cols-2 gap-3 text-sm">
        <Field label="Date" value={formatDate(appointment.appointment_date)} />
        <Field label="Time" value={formatTime(appointment.appointment_time)} />
      </dl>

      <div className="flex items-center justify-end border-t border-border pt-3">
        <Link
          to={`/appointments/${appointment.appointment_id}`}
          className={cn(
            "inline-flex min-h-[36px] items-center gap-1 rounded-md px-2 py-1 text-sm font-medium text-primary",
            "hover:text-primary/80",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          )}
        >
          Open full detail
          <ArrowUpRight className="size-3.5" strokeWidth={2} />
        </Link>
      </div>
    </article>
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
