import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Loader2 } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { AppointmentDetailView } from "@/components/appointments/AppointmentDetailView";
import { ApiErrorAlert } from "@/components/feedback/ApiErrorAlert";
import { NotFoundState } from "@/components/feedback/NotFoundState";
import { getAppointment } from "@/api/appointments";
import { ApiError } from "@/lib/apiClient";
import type { AppointmentResponse } from "@/types/api";
import { cn } from "@/lib/utils";

/**
 * `/appointments/:id` — full detail page.
 *
 * Query key `["appointment", id]` is shared with `/appointments`
 * (lookup) and with the reschedule/cancel mutations, so a successful
 * mutation reflected via `queryClient.setQueryData` shows up here
 * automatically on next render.
 */
export default function AppointmentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const appointmentId = id ?? "";

  const query = useQuery<AppointmentResponse, unknown>({
    queryKey: ["appointment", appointmentId],
    queryFn: ({ signal }) => getAppointment(appointmentId, signal),
    enabled: appointmentId.length > 0,
    retry: false,
  });

  const notFound =
    query.isError &&
    query.error instanceof ApiError &&
    query.error.code === "APPOINTMENT_NOT_FOUND";

  return (
    <AppShell>
      <PageHeader
        eyebrow="Appointment"
        title={query.data?.patient_name ?? appointmentId ?? "Appointment detail"}
        description={
          query.data
            ? `Full record for ${appointmentId}. Reschedule or cancel while the request is still open.`
            : "Full view of a single appointment."
        }
        actions={
          <Link
            to="/appointments"
            className={cn(
              "inline-flex min-h-[36px] items-center gap-1 rounded-md px-2 py-1 text-sm font-medium text-muted-foreground",
              "hover:text-foreground",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
            )}
          >
            <ArrowLeft className="size-4" strokeWidth={1.75} />
            Back to lookup
          </Link>
        }
      />

      <div className="mt-8">
        {query.isPending && (
          <div className="flex min-h-[240px] flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-card/50 p-10 text-center">
            <Loader2 className="size-6 animate-spin text-muted-foreground" strokeWidth={2} />
            <p className="mt-3 text-sm text-muted-foreground">
              Fetching appointment{" "}
              <span className="font-mono text-foreground">{appointmentId}</span>…
            </p>
          </div>
        )}

        {notFound && (
          <NotFoundState
            title="Appointment not found."
            description={`We couldn't find an appointment with ID "${appointmentId}".`}
            homeHref="/appointments"
            homeLabel="Back to lookup"
          />
        )}

        {query.isError && !notFound && (
          <ApiErrorAlert
            error={query.error}
            onRetry={() => query.refetch()}
            title="We couldn't load this appointment."
          />
        )}

        {query.isSuccess && <AppointmentDetailView appointment={query.data} />}
      </div>
    </AppShell>
  );
}
