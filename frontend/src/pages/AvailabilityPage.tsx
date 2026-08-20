import { useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { CalendarSearch, Loader2 } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { DoctorSelect } from "@/components/booking/DoctorSelect";
import { ServiceSelect } from "@/components/booking/ServiceSelect";
import { DateTimeFields } from "@/components/booking/DateTimeFields";
import { AvailabilityStatus } from "@/components/booking/AvailabilityStatus";
import { ApiErrorAlert } from "@/components/feedback/ApiErrorAlert";
import { checkAvailability } from "@/api/appointments";
import type { AvailabilityRequest, AvailabilityResponse } from "@/types/api";
import { cn } from "@/lib/utils";

/**
 * `/availability` — standalone availability checker.
 *
 * Simple form → live `POST /appointments/check-availability` via
 * React Query mutation → `AvailabilityStatus` card with the exact
 * message the backend returned. On unavailability, the card hands
 * off to the AI Assistant so the user can search for alternatives.
 */
export default function AvailabilityPage() {
  const [doctorId, setDoctorId] = useState("");
  const [service, setService] = useState("");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [touched, setTouched] = useState(false);

  const mutation = useMutation<AvailabilityResponse, unknown, AvailabilityRequest>({
    mutationFn: (body) => checkAvailability(body),
  });

  const missing = {
    doctor: !doctorId,
    date: !date,
    time: !time,
  };
  const hasErrors = missing.doctor || missing.date || missing.time;

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setTouched(true);
    if (hasErrors) return;
    mutation.mutate({
      doctor_id: doctorId,
      appointment_date: date,
      appointment_time: time,
      service: service || null,
    });
  }

  return (
    <AppShell>
      <PageHeader
        eyebrow="Availability"
        title="Check a specific slot"
        description="Pick a doctor, date, and time. CareFlow will tell you whether it's open — and the assistant can suggest alternatives if it isn't."
      />

      <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,4fr)]">
        {/* -------------------------------------------------------- */}
        {/* Form                                                      */}
        {/* -------------------------------------------------------- */}
        <form
          onSubmit={handleSubmit}
          noValidate
          aria-labelledby="availability-form-heading"
          className="rounded-2xl border border-border bg-card p-6"
        >
          <h2
            id="availability-form-heading"
            className="text-sm font-semibold tracking-tight text-foreground"
          >
            What would you like to check?
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Fields marked with a subtle border are required.
          </p>

          <div className="mt-5 flex flex-col gap-4">
            <DoctorSelect
              id="availability-doctor"
              value={doctorId}
              onChange={setDoctorId}
              error={touched && missing.doctor ? "Please select a doctor" : undefined}
              disabled={mutation.isPending}
            />

            <ServiceSelect
              id="availability-service"
              doctorId={doctorId}
              value={service}
              onChange={setService}
              disabled={mutation.isPending}
              optional
            />

            <DateTimeFields
              dateId="availability-date"
              timeId="availability-time"
              doctorId={doctorId}
              date={date}
              time={time}
              onDateChange={setDate}
              onTimeChange={setTime}
              dateError={touched && missing.date ? "Please pick a date" : undefined}
              timeError={touched && missing.time ? "Please pick a time" : undefined}
              disabled={mutation.isPending}
            />
          </div>

          <button
            type="submit"
            disabled={mutation.isPending}
            className={cn(
              "mt-6 inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground",
              "shadow-sm transition-colors hover:bg-primary/90",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              "disabled:cursor-not-allowed disabled:opacity-70",
            )}
          >
            {mutation.isPending ? (
              <>
                <Loader2 className="size-4 animate-spin" strokeWidth={2} />
                Checking…
              </>
            ) : (
              <>
                <CalendarSearch className="size-4" strokeWidth={1.75} />
                Check availability
              </>
            )}
          </button>
        </form>

        {/* -------------------------------------------------------- */}
        {/* Result column                                             */}
        {/* -------------------------------------------------------- */}
        <div className="flex min-h-[300px] flex-col">
          {mutation.isIdle && (
            <EmptyResult />
          )}

          {mutation.isPending && (
            <div className="flex flex-1 flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-card/50 p-10 text-center">
              <Loader2
                className="size-6 animate-spin text-muted-foreground"
                strokeWidth={2}
              />
              <p className="mt-3 text-sm text-muted-foreground">
                Contacting the CareFlow backend…
              </p>
            </div>
          )}

          {mutation.isError && (
            <ApiErrorAlert
              error={mutation.error}
              onRetry={() => mutation.reset()}
              title="We couldn't complete the availability check."
            />
          )}

          {mutation.isSuccess && (
            <AvailabilityStatus
              data={mutation.data}
              showAssistantHandoff={!mutation.data.available}
            />
          )}
        </div>
      </div>
    </AppShell>
  );
}

function EmptyResult() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-card/50 p-10 text-center">
      <span
        aria-hidden="true"
        className="inline-flex size-11 items-center justify-center rounded-full bg-muted text-muted-foreground"
      >
        <CalendarSearch className="size-5" strokeWidth={1.75} />
      </span>
      <p className="mt-4 text-sm font-medium text-foreground">
        Ready when you are.
      </p>
      <p className="mt-1 max-w-xs text-xs text-muted-foreground">
        Fill in the form and CareFlow will call the backend to see if the
        slot is open.
      </p>
    </div>
  );
}
