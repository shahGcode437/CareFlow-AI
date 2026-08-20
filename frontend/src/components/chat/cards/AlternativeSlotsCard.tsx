import { CalendarClock } from "lucide-react";
import type { AlternativeSlotsResponse } from "@/types/api";
import { formatDate, formatTime, trimSeconds } from "@/lib/format";
import { cn } from "@/lib/utils";

/**
 * `find_alternative_slots` result. Renders each slot as a
 * doctor/date/time card. Because the backend has no "book this slot"
 * endpoint that takes only doctor+date+time — creating an appointment
 * still requires patient_name, patient_phone, service, etc. — the
 * action here does NOT pretend to book. It hands the user a partial
 * message pre-filled with the slot fields so they can complete it in
 * the composer and send it as a normal chat.
 */

interface AlternativeSlotsCardProps {
  data: AlternativeSlotsResponse;
  onUseSlot?: (partialMessage: string) => void;
}

export function AlternativeSlotsCard({
  data,
  onUseSlot,
}: AlternativeSlotsCardProps) {
  if (data.alternatives.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-card p-4 text-sm text-muted-foreground">
        No alternative slots were found for the requested window.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-muted-foreground">
        <CalendarClock className="size-3.5" strokeWidth={2} />
        {data.alternatives.length} alternative
        {data.alternatives.length === 1 ? "" : "s"}
      </div>
      <ul className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
        {data.alternatives.map((slot, i) => {
          const partial = `Book with ${slot.doctor_name} (${slot.doctor_id}) on ${slot.appointment_date} at ${trimSeconds(slot.appointment_time)} — `;
          return (
            <li key={`${slot.doctor_id}-${slot.appointment_date}-${slot.appointment_time}-${i}`}>
              <button
                type="button"
                onClick={() => onUseSlot?.(partial)}
                disabled={!onUseSlot}
                className={cn(
                  "group flex w-full flex-col items-start rounded-lg border border-border bg-background p-3 text-left",
                  "transition-colors hover:border-primary/40 hover:bg-accent/30",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  "disabled:cursor-default disabled:opacity-70",
                )}
              >
                <span className="text-sm font-medium text-foreground">
                  {slot.doctor_name}
                </span>
                <span className="font-mono text-[11px] text-muted-foreground">
                  {slot.doctor_id}
                </span>
                <span className="mt-2 text-sm text-foreground">
                  {formatDate(slot.appointment_date)} · {formatTime(slot.appointment_time)}
                </span>
                {onUseSlot && (
                  <span className="mt-2 text-[11px] font-medium text-primary group-hover:underline">
                    Use this slot →
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
      {onUseSlot && (
        <p className="mt-3 text-[11px] text-muted-foreground">
          "Use this slot" prefills the composer — add your name, phone, and
          service before sending.
        </p>
      )}
    </div>
  );
}
