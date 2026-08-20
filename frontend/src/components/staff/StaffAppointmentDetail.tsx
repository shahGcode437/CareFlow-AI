import { useState } from "react";
import {
  CalendarClock,
  CheckCircle2,
  ClipboardList,
  Clock,
  User,
  XCircle,
} from "lucide-react";
import type { AppointmentResponse } from "@/types/api";
import { StatusPill } from "@/components/appointments/StatusPill";
import { formatDate, formatTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import { ApproveDialog } from "./ApproveDialog";
import { RejectDialog } from "./RejectDialog";

/**
 * Staff-facing full detail card. Distinct from the patient-facing
 * `AppointmentDetailView` because the actions differ: patients get
 * Reschedule / Cancel, staff get Approve / Reject on Pending records
 * only. Everything else (fields, formatting, status pill) uses the
 * same design-system tokens so both views feel like one product.
 */
export function StaffAppointmentDetail({
  appointment,
  demoStaffId,
}: {
  appointment: AppointmentResponse;
  demoStaffId: string;
}) {
  const [approveOpen, setApproveOpen] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);

  const isPending = appointment.status === "Pending";

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      {/* Left: patient / doctor / when / notes */}
      <section
        aria-labelledby="staff-detail-heading"
        className="rounded-2xl border border-border bg-card p-6 animate-fade-in-up"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
              Appointment ID
            </div>
            <div
              id="staff-detail-heading"
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

      {/* Right: staff actions + record */}
      <aside className="flex flex-col gap-4">
        <div className="rounded-2xl border border-border bg-card p-6 animate-fade-in-up">
          <h2 className="text-sm font-semibold tracking-tight text-foreground">
            Staff actions
          </h2>
          {isPending ? (
            <>
              <p className="mt-1 text-xs text-muted-foreground">
                Approve to Confirm, or Reject with a reason. Both actions
                are recorded on the appointment.
              </p>
              <div className="mt-4 flex flex-col gap-2">
                <button
                  type="button"
                  onClick={() => setApproveOpen(true)}
                  className={cn(
                    "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-md bg-status-confirmed px-4 py-2 text-sm font-medium text-status-confirmed-foreground",
                    "hover:brightness-95",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  )}
                >
                  <CheckCircle2 className="size-4" strokeWidth={1.75} />
                  Approve
                </button>
                <button
                  type="button"
                  onClick={() => setRejectOpen(true)}
                  className={cn(
                    "inline-flex min-h-[44px] items-center justify-center gap-2 rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-foreground",
                    "hover:bg-muted",
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  )}
                >
                  <XCircle className="size-4" strokeWidth={1.75} />
                  Reject with reason
                </button>
              </div>
            </>
          ) : (
            <p className="mt-3 text-sm text-muted-foreground">
              No further staff actions available for{" "}
              <span className="font-medium text-foreground">
                {appointment.status}
              </span>{" "}
              appointments. Approve/Reject apply only while a request is
              still <span className="font-medium">Pending</span>.
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

      <ApproveDialog
        open={approveOpen}
        onClose={() => setApproveOpen(false)}
        appointment={appointment}
        demoStaffId={demoStaffId}
      />
      <RejectDialog
        open={rejectOpen}
        onClose={() => setRejectOpen(false)}
        appointment={appointment}
        demoStaffId={demoStaffId}
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
