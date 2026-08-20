import { Link } from "react-router-dom";
import { CalendarClock, CheckCircle2, Sparkles, XCircle } from "lucide-react";
import type { AvailabilityResponse } from "@/types/api";
import { findDemoDoctor } from "@/config/clinic";
import { formatDate, formatTime } from "@/lib/format";
import { cn } from "@/lib/utils";

interface AvailabilityStatusProps {
  data: AvailabilityResponse;
  /** Shown only when unavailable — routes the user to /assistant. */
  showAssistantHandoff?: boolean;
  /** Optional trailing content — e.g. a "Confirm booking" button. */
  action?: React.ReactNode;
}

/**
 * Shared availability-result presentation. Same card is used by
 * `/availability` (standalone check) and `/book` (pre-flight check
 * before booking). Semantic status color makes the meaning legible at
 * a glance without depending on the icon alone.
 */
export function AvailabilityStatus({
  data,
  showAssistantHandoff,
  action,
}: AvailabilityStatusProps) {
  const doctor = findDemoDoctor(data.doctor_id);
  const StateIcon = data.available ? CheckCircle2 : XCircle;

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        "animate-fade-in-up rounded-2xl border p-5",
        data.available
          ? "border-status-confirmed/30 bg-status-confirmed/5"
          : "border-status-rejected/30 bg-status-rejected/5",
      )}
    >
      <div className="flex items-start gap-4">
        <span
          aria-hidden="true"
          className={cn(
            "inline-flex size-10 flex-shrink-0 items-center justify-center rounded-full",
            data.available
              ? "bg-status-confirmed/15 text-status-confirmed"
              : "bg-status-rejected/15 text-status-rejected",
          )}
        >
          <StateIcon className="size-5" strokeWidth={1.75} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-muted-foreground">
            <CalendarClock className="size-3.5" strokeWidth={2} />
            Availability check
          </div>
          <p
            className={cn(
              "mt-1 text-lg font-semibold tracking-tight",
              data.available ? "text-status-confirmed" : "text-status-rejected",
            )}
          >
            {data.available ? "Available" : "Not available"}
          </p>
          <p className="mt-1 text-sm text-muted-foreground">{data.message}</p>

          <dl className="mt-4 grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
            <Field
              label="Doctor"
              value={doctor ? `${doctor.name} · ${data.doctor_id}` : data.doctor_id}
            />
            <Field label="Date" value={formatDate(data.appointment_date)} />
            <Field label="Time" value={formatTime(data.appointment_time)} />
          </dl>

          {action && <div className="mt-5">{action}</div>}

          {!data.available && showAssistantHandoff && (
            <div className="mt-5 flex flex-col gap-2 border-t border-border pt-4 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-muted-foreground">
                Try the AI Assistant — it can search for alternative slots.
              </p>
              <Link
                to="/assistant"
                className={cn(
                  "inline-flex min-h-[44px] items-center gap-2 rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-foreground",
                  "hover:bg-muted",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                )}
              >
                <Sparkles className="size-4" strokeWidth={1.75} />
                Ask the assistant
              </Link>
            </div>
          )}
        </div>
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
      <dd className="mt-0.5 truncate text-sm font-medium text-foreground">
        {value}
      </dd>
    </div>
  );
}
