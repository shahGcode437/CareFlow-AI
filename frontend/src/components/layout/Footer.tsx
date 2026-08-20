import { HeartPulse } from "lucide-react";

/**
 * Quiet, informational footer. Non-clickable — nothing here should
 * pretend to be a real business page or live link.
 */
export function Footer() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-6 text-xs text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div className="flex items-center gap-2">
          <HeartPulse className="size-4 text-primary" strokeWidth={1.75} />
          <span>
            <span className="font-medium text-foreground">CareFlow AI</span>
            {" — "}
            Agentic appointment management for small clinics.
          </span>
        </div>
        <div className="text-[11px] uppercase tracking-widest">
          Capstone MVP · Demo data only
        </div>
      </div>
    </footer>
  );
}
