import { useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Loader2, ShieldCheck } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { StaffAppointmentDetail } from "@/components/staff/StaffAppointmentDetail";
import { ApiErrorAlert } from "@/components/feedback/ApiErrorAlert";
import { EmptyState } from "@/components/feedback/EmptyState";
import { NotFoundState } from "@/components/feedback/NotFoundState";
import { getAppointment } from "@/api/appointments";
import { ApiError } from "@/lib/apiClient";
import type { AppointmentResponse } from "@/types/api";
import { cn } from "@/lib/utils";

/**
 * `/staff` — clinic staff console (demo mode).
 *
 * Look up any appointment by ID, review its full record, and approve
 * or reject it while it's still Pending. All wire-level calls go
 * through the Phase 8.2 API modules (`@/api/staff`,
 * `@/api/appointments`) — this page adds only the UI layer.
 *
 * Authentication is NOT implemented server-side: the amber banner at
 * the top of the page makes that limitation impossible to miss, and
 * both dialogs echo the same `is_staff` / `staff_id` placeholder
 * disclosure.
 */

const DEMO_STAFF_ID = "STAFF-DEMO";

export default function StaffPage() {
  const [inputId, setInputId] = useState("");
  const [submittedId, setSubmittedId] = useState<string | null>(null);
  const [touched, setTouched] = useState(false);

  const trimmed = inputId.trim();
  const inputError =
    touched && trimmed.length === 0
      ? "Enter an appointment ID (e.g. APT-001)."
      : undefined;

  const query = useQuery<AppointmentResponse, unknown>({
    queryKey: ["appointment", submittedId],
    queryFn: ({ signal }) => getAppointment(submittedId as string, signal),
    enabled: !!submittedId,
    retry: false,
  });

  const notFound =
    query.isError &&
    query.error instanceof ApiError &&
    query.error.code === "APPOINTMENT_NOT_FOUND";

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setTouched(true);
    if (!trimmed) return;
    setSubmittedId(trimmed);
  }

  return (
    <AppShell>
      <PageHeader
        eyebrow="Staff console"
        title="Approve or reject a request"
        description="Look up a pending appointment by ID and take action. Actions are only offered while the request is still Pending."
      />

      {/* Demo-auth notice — always visible, never dismissible. */}
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
          <p className="font-medium text-foreground">
            Demo mode — not secured.
          </p>
          <p className="mt-0.5 text-muted-foreground">
            The current backend has no staff authentication. Any caller can
            assert <span className="font-mono text-xs">is_staff</span>. A real
            deployment will need an authentication boundary first.
          </p>
        </div>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,4fr)]">
        {/* Lookup form */}
        <form
          onSubmit={handleSubmit}
          noValidate
          aria-labelledby="staff-lookup-heading"
          className="rounded-2xl border border-border bg-card p-6"
        >
          <h2
            id="staff-lookup-heading"
            className="text-sm font-semibold tracking-tight text-foreground"
          >
            Load appointment
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            IDs are case-sensitive and start with{" "}
            <code className="rounded bg-muted px-1 py-0.5 font-mono">APT-</code>.
          </p>

          <div className="mt-5 flex flex-col gap-1.5">
            <label htmlFor="staff-appointment-id" className="sr-only">
              Appointment ID
            </label>
            <div className="relative">
              <ShieldCheck
                className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                strokeWidth={1.75}
                aria-hidden="true"
              />
              <input
                id="staff-appointment-id"
                type="text"
                inputMode="text"
                autoComplete="off"
                spellCheck={false}
                placeholder="APT-001"
                value={inputId}
                onChange={(e) => setInputId(e.target.value)}
                disabled={query.isFetching}
                aria-invalid={!!inputError}
                aria-describedby={
                  inputError ? "staff-appointment-id-error" : undefined
                }
                className={cn(
                  "min-h-[44px] w-full rounded-md border border-border bg-background pl-9 pr-3 py-2 text-sm font-mono text-foreground",
                  "placeholder:font-sans placeholder:text-muted-foreground",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  "disabled:cursor-not-allowed disabled:opacity-60",
                  inputError && "border-destructive/60",
                )}
              />
            </div>
            {inputError && (
              <p
                id="staff-appointment-id-error"
                className="text-xs text-destructive"
              >
                {inputError}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={query.isFetching}
            className={cn(
              "mt-5 inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground",
              "shadow-sm transition-colors hover:bg-primary/90",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              "disabled:cursor-not-allowed disabled:opacity-70",
            )}
          >
            {query.isFetching ? (
              <>
                <Loader2 className="size-4 animate-spin" strokeWidth={2} />
                Loading…
              </>
            ) : (
              <>
                <ShieldCheck className="size-4" strokeWidth={1.75} />
                Load appointment
              </>
            )}
          </button>

          <p className="mt-4 text-[11px] text-muted-foreground">
            All staff actions include{" "}
            <code className="rounded bg-muted px-1 py-0.5 font-mono">
              is_staff: true, staff_id: "{DEMO_STAFF_ID}"
            </code>{" "}
            — demo placeholders, no real auth.
          </p>
        </form>

        {/* Result column */}
        <div className="flex min-h-[240px] flex-col">
          {!submittedId && (
            <EmptyState
              icon={ShieldCheck}
              title="No appointment loaded yet."
              description="Enter an appointment ID above to review it and take action."
            />
          )}

          {submittedId && query.isFetching && (
            <div className="flex flex-1 flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-card/50 p-10 text-center">
              <Loader2
                className="size-6 animate-spin text-muted-foreground"
                strokeWidth={2}
              />
              <p className="mt-3 text-sm text-muted-foreground">
                Fetching{" "}
                <span className="font-mono text-foreground">{submittedId}</span>
                …
              </p>
            </div>
          )}

          {submittedId && notFound && (
            <NotFoundState
              title="Appointment not found."
              description={`No appointment with ID "${submittedId}". Double-check the ID and try again.`}
              homeHref="/staff"
            homeLabel="Try another ID"
            />
          )}

          {submittedId && query.isError && !notFound && (
            <ApiErrorAlert
              error={query.error}
              onRetry={() => query.refetch()}
              title="We couldn't load that appointment."
            />
          )}

          {submittedId && query.isSuccess && (
            <StaffAppointmentDetail
              appointment={query.data}
              demoStaffId={DEMO_STAFF_ID}
            />
          )}
        </div>
      </div>
    </AppShell>
  );
}
