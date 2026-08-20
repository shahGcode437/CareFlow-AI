import { ChevronDown, Stethoscope } from "lucide-react";
import { DEMO_DOCTORS } from "@/config/clinic";
import { cn } from "@/lib/utils";

interface DoctorSelectProps {
  id: string;
  value: string;
  onChange: (doctorId: string) => void;
  error?: string;
  disabled?: boolean;
  className?: string;
}

/**
 * Native `<select>` styled to match the design system.
 *
 * The rationale for native: it's fully accessible for keyboard/screen-
 * reader users, works well on mobile (opens the OS wheel), and doesn't
 * pull in another shadcn primitive for a two-option list. If we later
 * grow beyond a handful of doctors from a real endpoint, this can be
 * swapped for `<Select/>` without touching consumers.
 */
export function DoctorSelect({
  id,
  value,
  onChange,
  error,
  disabled,
  className,
}: DoctorSelectProps) {
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label
        htmlFor={id}
        className="text-xs font-medium uppercase tracking-widest text-muted-foreground"
      >
        Doctor
      </label>
      <div className="relative">
        <Stethoscope
          className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
          strokeWidth={1.75}
          aria-hidden="true"
        />
        <select
          id={id}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-error` : undefined}
          className={cn(
            "min-h-[44px] w-full appearance-none rounded-md border border-border bg-background pl-9 pr-9 py-2 text-sm text-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
            "disabled:cursor-not-allowed disabled:opacity-60",
            error && "border-destructive/60",
          )}
        >
          <option value="">Select a doctor</option>
          {DEMO_DOCTORS.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name} · {d.specialty}
            </option>
          ))}
        </select>
        <ChevronDown
          className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
          strokeWidth={1.75}
          aria-hidden="true"
        />
      </div>
      {error && (
        <p id={`${id}-error`} className="text-xs text-destructive">
          {error}
        </p>
      )}
      <p className="text-[11px] text-muted-foreground">
        Demo seed: two doctors. Backend remains authoritative.
      </p>
    </div>
  );
}
