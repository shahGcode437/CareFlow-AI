import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { PlaceholderPanel } from "@/components/layout/PlaceholderPanel";

export default function AppointmentsPage() {
  return (
    <AppShell>
      <PageHeader
        eyebrow="Find appointment"
        title="Look up your appointment"
        description="Enter your appointment ID (e.g. APT-001) to view details, reschedule, or cancel."
      />
      <div className="mt-8">
        <PlaceholderPanel
          route="/appointments"
          phase="Phase 8.7"
          endpoint="GET /appointments/{id}"
        />
      </div>
    </AppShell>
  );
}
