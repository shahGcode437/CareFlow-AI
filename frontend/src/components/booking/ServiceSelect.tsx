import { useEffect } from "react";
import { ChevronDown, ClipboardList } from "lucide-react";
import { findDemoDoctor } from "@/config/clinic";
import { cn } from "@/lib/utils";

interface ServiceSelectProps {
  id: string;
  doctorId: string;
  value: string;
  onChange: (service: string) => void;
  error?: string;
  disabled?: boolean;
  optional?: boolean;
  className?: string;
}

/**
 * Service selector — options are derived from the currently selected
 * doctor. If the doctor changes, we clear the previously chosen
 * service so we never carry a service that doesn't belong to the new
 * doctor.
 */
export function ServiceSelect({
  id,
  doctorId,
  value,
  onChange,
  error,
  disabled,
  optional,
  className,
}: ServiceSelectProps) {
  const doctor = findDemoDoctor(doctorId);

  useEffect(() => {
    // Clear service if it no longer belongs to the selected doctor.
    if (value && (!doctor || !doctor.services.includes(value))) {
      onChange("");
    }
    // Do NOT depend on `onChange` (would loop on inline arrows).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doctorId]);

  const noDoctor = !doctorId;

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label
        htmlFor={id}
        className="text-xs font-medium uppercase tracking-widest text-muted-foreground"
      >
        Service{optional ? " (optional)" : ""}
      </label>
      <div className="relative">
        <ClipboardList
          className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
          strokeWidth={1.75}
          aria-hidden="true"
        />
        <select
          id={id}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled || noDoctor}
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-error` : undefined}
          className={cn(
            "min-h-[44px] w-full appearance-none rounded-md border border-border bg-background pl-9 pr-9 py-2 text-sm text-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
            "disabled:cursor-not-allowed disabled:opacity-60",
            error && "border-destructive/60",
          )}
        >
          <option value="">
            {noDoctor
              ? "Select a doctor first"
              : optional
                ? "Any service"
                : "Select a service"}
          </option>
          {doctor?.services.map((s) => (
            <option key={s} value={s}>
              {s}
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
    </div>
  );
}
