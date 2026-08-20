import { useState } from "react";
import { Phone, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Inline "session settings" — patient phone is optional and lives in
 * memory only (see `useChatSession`). We collect it here so a booking
 * flow through the assistant can reference an identity without the
 * user retyping it every message.
 */
export function PatientPhoneField({
  value,
  onChange,
}: {
  value: string | null;
  onChange: (next: string | null) => void;
}) {
  const [draft, setDraft] = useState(value ?? "");

  const applied = value !== null && value === draft.trim();

  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-muted-foreground">
        <Phone className="size-3.5" strokeWidth={2} />
        Patient phone (optional)
      </div>
      <p className="mt-1 text-xs text-muted-foreground">
        Attached to your requests only. Stored in this browser tab, not
        persisted or logged.
      </p>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row">
        <label htmlFor="patient-phone-input" className="sr-only">
          Patient phone number
        </label>
        <input
          id="patient-phone-input"
          type="tel"
          inputMode="tel"
          autoComplete="tel"
          placeholder="03000000000"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          className={cn(
            "min-h-[44px] flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground",
            "placeholder:text-muted-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          )}
        />
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onChange(draft || null)}
            disabled={!draft.trim() || applied}
            className={cn(
              "inline-flex min-h-[44px] items-center justify-center rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground",
              "hover:bg-primary/90",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              "disabled:cursor-not-allowed disabled:opacity-60",
            )}
          >
            {applied ? "Applied" : "Apply"}
          </button>
          {value !== null && (
            <button
              type="button"
              onClick={() => {
                setDraft("");
                onChange(null);
              }}
              aria-label="Clear patient phone"
              className={cn(
                "inline-flex size-11 items-center justify-center rounded-md border border-border text-muted-foreground",
                "hover:bg-muted hover:text-foreground",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              )}
            >
              <Trash2 className="size-4" strokeWidth={1.75} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
