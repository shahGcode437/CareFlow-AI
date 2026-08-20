import { CalendarDays, Clock } from "lucide-react";
import { findDemoDoctor, weekdayName } from "@/config/clinic";
import { cn } from "@/lib/utils";

interface DateTimeFieldsProps {
  dateId: string;
  timeId: string;
  doctorId: string;
  date: string;
  time: string;
  onDateChange: (value: string) => void;
  onTimeChange: (value: string) => void;
  dateError?: string;
  timeError?: string;
  disabled?: boolean;
}

/**
 * Native date + time inputs, wrapped for consistent styling.
 *
 *   - Native `<input type="date">` / `type="time">` give us the OS
 *     picker on mobile and full keyboard support on desktop for free.
 *   - `<input type="time" step="60">` forces `HH:MM` output — exactly
 *     what the backend accepts.
 *   - When both a doctor and a date are chosen, we surface a subtle
 *     hint if the picked weekday isn't in the seed doctor's
 *     `availableDays`. We do NOT block the request — the backend
 *     stays authoritative on availability.
 */
export function DateTimeFields({
  dateId,
  timeId,
  doctorId,
  date,
  time,
  onDateChange,
  onTimeChange,
  dateError,
  timeError,
  disabled,
}: DateTimeFieldsProps) {
  const doctor = findDemoDoctor(doctorId);
  const pickedWeekday = date ? weekdayName(date) : null;

  const weekdayHint =
    doctor && pickedWeekday && !doctor.availableDays.includes(pickedWeekday)
      ? `Heads-up: ${doctor.name} isn't scheduled on ${pickedWeekday} in the seed data. The backend will confirm.`
      : null;

  const hoursHint = doctor
    ? `${doctor.name} · ${doctor.availableDays.join(", ")} · ${doctor.hours.start}–${doctor.hours.end} (${doctor.hours.slotMinutes} min slots)`
    : null;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-4 sm:flex-row">
        <div className="flex flex-1 flex-col gap-1.5">
          <label
            htmlFor={dateId}
            className="text-xs font-medium uppercase tracking-widest text-muted-foreground"
          >
            Date
          </label>
          <div className="relative">
            <CalendarDays
              className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
              strokeWidth={1.75}
              aria-hidden="true"
            />
            <input
              id={dateId}
              type="date"
              value={date}
              onChange={(e) => onDateChange(e.target.value)}
              disabled={disabled}
              aria-invalid={!!dateError}
              aria-describedby={dateError ? `${dateId}-error` : undefined}
              className={cn(
                "min-h-[44px] w-full rounded-md border border-border bg-background pl-9 pr-3 py-2 text-sm text-foreground",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                "disabled:cursor-not-allowed disabled:opacity-60",
                dateError && "border-destructive/60",
              )}
            />
          </div>
          {dateError && (
            <p id={`${dateId}-error`} className="text-xs text-destructive">
              {dateError}
            </p>
          )}
        </div>

        <div className="flex flex-1 flex-col gap-1.5">
          <label
            htmlFor={timeId}
            className="text-xs font-medium uppercase tracking-widest text-muted-foreground"
          >
            Time
          </label>
          <div className="relative">
            <Clock
              className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
              strokeWidth={1.75}
              aria-hidden="true"
            />
            <input
              id={timeId}
              type="time"
              step={60}
              value={time}
              onChange={(e) => onTimeChange(e.target.value)}
              disabled={disabled}
              aria-invalid={!!timeError}
              aria-describedby={timeError ? `${timeId}-error` : undefined}
              className={cn(
                "min-h-[44px] w-full rounded-md border border-border bg-background pl-9 pr-3 py-2 text-sm text-foreground",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                "disabled:cursor-not-allowed disabled:opacity-60",
                timeError && "border-destructive/60",
              )}
            />
          </div>
          {timeError && (
            <p id={`${timeId}-error`} className="text-xs text-destructive">
              {timeError}
            </p>
          )}
        </div>
      </div>

      {(weekdayHint || hoursHint) && (
        <div aria-live="polite">
          {weekdayHint && (
            <p className="text-xs text-status-pending">{weekdayHint}</p>
          )}
          {hoursHint && (
            <p className="text-[11px] text-muted-foreground">{hoursHint}</p>
          )}
        </div>
      )}
    </div>
  );
}
