import { useParams } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { PlaceholderPanel } from "@/components/layout/PlaceholderPanel";

export default function AppointmentDetailPage() {
  const { id } = useParams<{ id: string }>();
  return (
    <AppShell>
      <PageHeader
        eyebrow="Appointment"
        title={id ?? "Appointment detail"}
        description="Full view of a single appointment. Reschedule, cancel, or trigger staff actions from here."
      />
      <div className="mt-8">
        <PlaceholderPanel
          route={`/appointments/${id ?? ":id"}`}
          phase="Phase 8.7"
          endpoint="GET · PATCH · POST /appointments/{id}/cancel"
        />
      </div>
    </AppShell>
  );
}
