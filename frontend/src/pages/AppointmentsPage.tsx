import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Loader2, Search } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { AppointmentCard } from "@/components/appointments/AppointmentCard";
import { ApiErrorAlert } from "@/components/feedback/ApiErrorAlert";
import { EmptyState } from "@/components/feedback/EmptyState";
import { NotFoundState } from "@/components/feedback/NotFoundState";
import { getAppointment } from "@/api/appointments";
import { ApiError } from "@/lib/apiClient";
import type { AppointmentResponse } from "@/types/api";
import { cn } from "@/lib/utils";

/**
 * `/appointments` — look up an appointment by ID.
 *
 * The form posts to a client-side "submittedId" state, which becomes
 * the enabled React Query. That way the query key `["appointment", id]`
 * is stable across component instances (the detail page uses the same
 * key), so a mutation on `/appointments/:id` invalidates in one place.
 */
export default function AppointmentsPage() {
  const [inputId, setInputId] = useState("");
  const [submittedId, setSubmittedId] = useState<string | null>(null);
  const [touched, setTouched] = useState(false);
  const navigate = useNavigate();

  const trimmed = inputId.trim();
  const inputError = touched && trimmed.length === 0
    ? "Please enter your appointment ID (e.g. APT-001)."
    : undefined;

  const query = useQuery<AppointmentResponse, unknown>({
    queryKey: ["appointment", submittedId],
    queryFn: ({ signal }) => getAppointment(submittedId as string, signal),
    enabled: !!submittedId,
    retry: false,
  });

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setTouched(true);
    if (!trimmed) return;
    setSubmittedId(trimmed);
  }

  const notFound =
    query.isError &&
    query.error instanceof ApiError &&
    query.error.code === "APPOINTMENT_NOT_FOUND";

  return (
    <AppShell>
      <PageHeader
        eyebrow="Find appointment"
        title="Look up your appointment"
        description="Enter the appointment ID from your confirmation to view details, reschedule, or cancel."
      />

      <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,4fr)]">
        {/* ---------------------------------------------------------- */}
        {/* Search form                                                 */}
        {/* ---------------------------------------------------------- */}
        <form
          onSubmit={handleSubmit}
          noValidate
          aria-labelledby="lookup-form-heading"
          className="rounded-2xl border border-border bg-card p-6"
        >
          <h2
            id="lookup-form-heading"
            className="text-sm font-semibold tracking-tight text-foreground"
          >
            Enter appointment ID
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            IDs start with <code className="rounded bg-muted px-1 py-0.5 font-mono">APT-</code>. Case-sensitive.
          </p>

          <div className="mt-5 flex flex-col gap-1.5">
            <label
              htmlFor="appointment-id"
              className="sr-only"
            >
              Appointment ID
            </label>
            <div className="relative">
              <Search
                className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                strokeWidth={1.75}
                aria-hidden="true"
              />
              <input
                id="appointment-id"
                type="text"
                inputMode="text"
                autoComplete="off"
                spellCheck={false}
                placeholder="APT-001"
                value={inputId}
                onChange={(e) => setInputId(e.target.value)}
                disabled={query.isFetching}
                aria-invalid={!!inputError}
                aria-describedby={inputError ? "appointment-id-error" : undefined}
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
              <p id="appointment-id-error" className="text-xs text-destructive">
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
                Looking up…
              </>
            ) : (
              <>
                <Search className="size-4" strokeWidth={1.75} />
                Find appointment
              </>
            )}
          </button>
        </form>

        {/* ---------------------------------------------------------- */}
        {/* Result column                                               */}
        {/* ---------------------------------------------------------- */}
        <div className="flex min-h-[240px] flex-col">
          {!submittedId && (
            <EmptyState
              icon={Search}
              title="No lookup yet."
              description="Enter an appointment ID above to fetch its current details from the backend."
            />
          )}

          {submittedId && query.isFetching && (
            <div className="flex flex-1 flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-card/50 p-10 text-center">
              <Loader2 className="size-6 animate-spin text-muted-foreground" strokeWidth={2} />
              <p className="mt-3 text-sm text-muted-foreground">
                Fetching appointment{" "}
                <span className="font-mono text-foreground">{submittedId}</span>…
              </p>
            </div>
          )}

          {submittedId && notFound && (
            <NotFoundState
              title="Appointment not found."
              description={`We couldn't find an appointment with ID "${submittedId}". Double-check the ID from your confirmation.`}
              homeHref="/appointments"
            homeLabel="Try another ID"
            />
          )}

          {submittedId && query.isError && !notFound && (
            <ApiErrorAlert
              error={query.error}
              onRetry={() => query.refetch()}
              title="We couldn't complete the lookup."
            />
          )}

          {submittedId && query.isSuccess && (
            <div className="flex flex-col gap-4">
              <AppointmentCard appointment={query.data} />
              <button
                type="button"
                onClick={() =>
                  navigate(`/appointments/${query.data.appointment_id}`)
                }
                className={cn(
                  "inline-flex min-h-[44px] items-center justify-center gap-2 self-start rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground",
                  "hover:bg-primary/90",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                )}
              >
                Open full detail
              </button>
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
