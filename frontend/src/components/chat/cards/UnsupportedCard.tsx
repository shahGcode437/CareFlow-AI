import { HelpCircle } from "lucide-react";

/**
 * `unsupported` and `error` intents both use this card. Kept minimal
 * — the assistant's own message text carries the explanation; this
 * block just adds a subtle visual anchor so the reader can tell at a
 * glance that the assistant declined rather than replied with data.
 */
export function UnsupportedCard({ tone }: { tone: "unsupported" | "error" }) {
  const label =
    tone === "error" ? "Something went wrong" : "Not something CareFlow can do yet";
  return (
    <div className="rounded-xl border border-border bg-muted/50 p-4">
      <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-widest text-muted-foreground">
        <HelpCircle className="size-3.5" strokeWidth={2} />
        {label}
      </div>
    </div>
  );
}
