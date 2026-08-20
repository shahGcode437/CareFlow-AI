import { AlertTriangle } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { PlaceholderPanel } from "@/components/layout/PlaceholderPanel";

export default function StaffPage() {
  return (
    <AppShell>
      <PageHeader
        eyebrow="Staff console"
        title="Approve or reject a request"
        description="Look up a pending appointment by ID and take action. Auth is not implemented server-side yet — see the notice below."
      />

      {/* Demo-auth notice. Present now so the shape of the page reads
          honestly during design review; the real staff console will
          replace this in Phase 8.8. */}
      <div
        role="note"
        className="mt-8 flex items-start gap-3 rounded-lg border border-status-pending/40 bg-status-pending/10 p-4 text-sm"
      >
        <AlertTriangle
          className="mt-0.5 size-4 flex-shrink-0 text-status-pending"
          strokeWidth={1.75}
          aria-hidden="true"
        />
        <div>
          <p className="font-medium text-foreground">Demo mode — not secured.</p>
          <p className="mt-0.5 text-muted-foreground">
            The current backend has no staff authentication. Any caller can
            assert <span className="font-mono text-xs">is_staff</span>. A real
            deployment will need an authentication boundary first.
          </p>
        </div>
      </div>

      <div className="mt-6">
        <PlaceholderPanel
          route="/staff"
          phase="Phase 8.8"
          endpoint="POST /staff/appointments/{id}/{approve,reject}"
        />
      </div>
    </AppShell>
  );
}
