import { findDemoDoctor } from "@/config/clinic";
import { formatDate, formatTime } from "@/lib/format";

interface BookingSummaryProps {
  patientName: string;
  patientPhone: string;
  doctorId: string;
  service: string;
  appointmentDate: string;
  appointmentTime: string;
  notes?: string;
}

/**
 * Read-only summary shown between the availability confirmation and
 * the final "Confirm booking" click. Gives the user one last chance
 * to spot a typo before we hit `POST /appointments`.
 */
export function BookingSummary(props: BookingSummaryProps) {
  const doctor = findDemoDoctor(props.doctorId);
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
        Review your request
      </div>
      <dl className="mt-3 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
        <Field label="Patient" value={props.patientName} />
        <Field label="Phone" value={props.patientPhone} mono />
        <Field
          label="Doctor"
          value={doctor ? `${doctor.name} · ${props.doctorId}` : props.doctorId}
        />
        <Field label="Service" value={props.service} />
        <Field label="Date" value={formatDate(props.appointmentDate)} />
        <Field label="Time" value={formatTime(props.appointmentTime)} />
      </dl>
      {props.notes && (
        <p className="mt-4 rounded-md bg-muted px-3 py-2 text-xs text-muted-foreground">
          <span className="font-medium text-foreground">Notes:</span>{" "}
          {props.notes}
        </p>
      )}
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
