import { CalendarClock, CheckCircle2, XCircle } from "lucide-react";
import type { AvailabilityResponse } from "@/types/api";
import { formatDate, formatTime } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * `check_availability` result — shows the requested slot with a clear
 * available / unavailable state and the doctor/date/time it was
 * checked against.
 */
export function AvailabilityResultCard({
  data,
}: {
  data: AvailabilityResponse;
}) {
  const StateIcon = data.available ? CheckCircle2 : XCircle;
  const stateClass = data.available
    ? "text-status-confirmed"
    : "text-status-rejected";

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-muted-foreground">
          <CalendarClock className="size-3.5" strokeWidth={2} />
          Availability check
        </div>
        <div className={cn("flex items-center gap-1.5 text-xs font-medium", stateClass)}>
          <StateIcon className="size-3.5" strokeWidth={2} />
          {data.available ? "Available" : "Unavailable"}
        </div>
      </div>

      <dl className="mt-3 grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
        <Field label="Doctor" value={data.doctor_id} mono />
        <Field label="Date" value={formatDate(data.appointment_date)} />
        <Field label="Time" value={formatTime(data.appointment_time)} />
      </dl>
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
        className={cn(
          "mt-0.5 truncate text-sm text-foreground",
          mono && "font-mono",
        )}
      >
        {value}
      </dd>
    </div>
  );
}
