import { forwardRef, useEffect, useState, type InputHTMLAttributes } from "react";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { z } from "zod";
import {
  CalendarSearch,
  ClipboardCheck,
  Loader2,
  Phone,
  UserRound,
} from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { DoctorSelect } from "@/components/booking/DoctorSelect";
import { ServiceSelect } from "@/components/booking/ServiceSelect";
import { DateTimeFields } from "@/components/booking/DateTimeFields";
import { AvailabilityStatus } from "@/components/booking/AvailabilityStatus";
import { BookingSummary } from "@/components/booking/BookingSummary";
import { BookingSuccess } from "@/components/booking/BookingSuccess";
import { ApiErrorAlert } from "@/components/feedback/ApiErrorAlert";
import { checkAvailability, createAppointment } from "@/api/appointments";
import type {
  AppointmentCreate,
  AppointmentResponse,
  AvailabilityRequest,
  AvailabilityResponse,
} from "@/types/api";
import { findDemoDoctor } from "@/config/clinic";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ */
/* Zod schema — mirrors the AppointmentCreate contract in api.ts.     */
/* Client-side validation only; the backend remains authoritative.    */
/* ------------------------------------------------------------------ */

const bookingSchema = z.object({
  patient_name: z.string().trim().min(2, "Please enter at least 2 characters."),
  patient_phone: z.string().trim().min(1, "A contact number is required."),
  doctor_id: z.string().min(1, "Please select a doctor."),
  service: z.string().min(1, "Please select a service."),
  appointment_date: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/, "Please pick a valid date."),
  appointment_time: z
    .string()
    .regex(/^\d{2}:\d{2}(:\d{2})?$/, "Please pick a valid time."),
  notes: z
    .string()
    .max(500, "Please keep notes under 500 characters.")
    .optional()
    .or(z.literal("")),
});

type BookingFormValues = z.infer<typeof bookingSchema>;

const DEFAULT_VALUES: BookingFormValues = {
  patient_name: "",
  patient_phone: "",
  doctor_id: "",
  service: "",
  appointment_date: "",
  appointment_time: "",
  notes: "",
};

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export default function BookAppointmentPage() {
  const [bookedAppointment, setBookedAppointment] =
    useState<AppointmentResponse | null>(null);

  const form = useForm<BookingFormValues>({
    resolver: zodResolver(bookingSchema),
    mode: "onBlur",
    defaultValues: DEFAULT_VALUES,
  });
  const {
    control,
    register,
    handleSubmit,
    watch,
    getValues,
    reset,
    formState: { errors, isValid },
  } = form;

  const checkMutation = useMutation<
    AvailabilityResponse,
    unknown,
    AvailabilityRequest
  >({
    mutationFn: (body) => checkAvailability(body),
  });

  const bookMutation = useMutation<
    AppointmentResponse,
    unknown,
    AppointmentCreate
  >({
    mutationFn: (body) => createAppointment(body),
    onSuccess: (data) => {
      setBookedAppointment(data);
    },
  });

  // Any change to an availability-relevant field invalidates the
  // "checked" state so the user has to re-check before confirming.
  const doctorId = watch("doctor_id");
  const service = watch("service");
  const date = watch("appointment_date");
  const time = watch("appointment_time");
  useEffect(() => {
    if (checkMutation.status !== "idle") checkMutation.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doctorId, service, date, time]);

  if (bookedAppointment) {
    return (
      <AppShell>
        <PageHeader
          eyebrow="Booked"
          title="Appointment on file"
          description="CareFlow has recorded your request. Details are shown below — you can also open the full appointment page anytime."
        />
        <div className="mt-8">
          <BookingSuccess
            appointment={bookedAppointment}
            onBookAnother={() => {
              setBookedAppointment(null);
              bookMutation.reset();
              checkMutation.reset();
              reset(DEFAULT_VALUES);
            }}
          />
        </div>
      </AppShell>
    );
  }

  const availabilityData = checkMutation.data;
  const isAvailable = availabilityData?.available === true;

  function handleCheck(values: BookingFormValues) {
    checkMutation.mutate({
      doctor_id: values.doctor_id,
      appointment_date: values.appointment_date,
      appointment_time: values.appointment_time,
      service: values.service || null,
    });
  }

  function handleConfirmBooking() {
    const values = getValues();
    const doctor = findDemoDoctor(values.doctor_id);
    if (!doctor) return; // Should never happen — form validation prevents it.
    const body: AppointmentCreate = {
      patient_name: values.patient_name.trim(),
      patient_phone: values.patient_phone.trim(),
      doctor_id: values.doctor_id,
      doctor_name: doctor.name,
      service: values.service,
      appointment_date: values.appointment_date,
      appointment_time: values.appointment_time,
      notes: values.notes && values.notes.trim().length > 0
        ? values.notes.trim()
        : null,
    };
    bookMutation.mutate(body);
  }

  return (
    <AppShell>
      <PageHeader
        eyebrow="Book"
        title="Request an appointment"
        description="Fill in your details, then CareFlow will check the slot with the backend before creating the appointment. Nothing is committed until you confirm."
      />

      <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        {/* ---------------------------------------------------------- */}
        {/* Form                                                        */}
        {/* ---------------------------------------------------------- */}
        <form
          onSubmit={handleSubmit(handleCheck)}
          noValidate
          aria-labelledby="booking-form-heading"
          className="rounded-2xl border border-border bg-card p-6"
        >
          <h2
            id="booking-form-heading"
            className="text-sm font-semibold tracking-tight text-foreground"
          >
            Appointment details
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            All fields are required. Backend validation still runs on submit.
          </p>

          <div className="mt-6 flex flex-col gap-5">
            <TextField
              id="patient_name"
              label="Full name"
              icon={UserRound}
              placeholder="e.g. Adnan Shah"
              autoComplete="name"
              disabled={bookMutation.isPending}
              error={errors.patient_name?.message}
              {...register("patient_name")}
            />

            <TextField
              id="patient_phone"
              label="Phone number"
              icon={Phone}
              placeholder="03000000000"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              disabled={bookMutation.isPending}
              error={errors.patient_phone?.message}
              {...register("patient_phone")}
            />

            <Controller
              control={control}
              name="doctor_id"
              render={({ field }) => (
                <DoctorSelect
                  id="doctor_id"
                  value={field.value}
                  onChange={field.onChange}
                  error={errors.doctor_id?.message}
                  disabled={bookMutation.isPending}
                />
              )}
            />

            <Controller
              control={control}
              name="service"
              render={({ field }) => (
                <ServiceSelect
                  id="service"
                  doctorId={doctorId}
                  value={field.value}
                  onChange={field.onChange}
                  error={errors.service?.message}
                  disabled={bookMutation.isPending}
                />
              )}
            />

            <Controller
              control={control}
              name="appointment_date"
              render={({ field: dateField }) => (
                <Controller
                  control={control}
                  name="appointment_time"
                  render={({ field: timeField }) => (
                    <DateTimeFields
                      dateId="appointment_date"
                      timeId="appointment_time"
                      doctorId={doctorId}
                      date={dateField.value}
                      time={timeField.value}
                      onDateChange={dateField.onChange}
                      onTimeChange={timeField.onChange}
                      dateError={errors.appointment_date?.message}
                      timeError={errors.appointment_time?.message}
                      disabled={bookMutation.isPending}
                    />
                  )}
                />
              )}
            />

            <div className="flex flex-col gap-1.5">
              <label
                htmlFor="notes"
                className="text-xs font-medium uppercase tracking-widest text-muted-foreground"
              >
                Notes (optional)
              </label>
              <textarea
                id="notes"
                rows={3}
                placeholder="Anything the clinic should know before your visit."
                disabled={bookMutation.isPending}
                aria-invalid={!!errors.notes}
                aria-describedby={errors.notes ? "notes-error" : undefined}
                className={cn(
                  "min-h-[88px] w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground",
                  "placeholder:text-muted-foreground",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  "disabled:cursor-not-allowed disabled:opacity-60",
                  errors.notes && "border-destructive/60",
                )}
                {...register("notes")}
              />
              {errors.notes?.message && (
                <p id="notes-error" className="text-xs text-destructive">
                  {errors.notes.message}
                </p>
              )}
            </div>
          </div>

          <button
            type="submit"
            disabled={checkMutation.isPending || bookMutation.isPending}
            className={cn(
              "mt-6 inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-md bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground",
              "shadow-sm transition-colors hover:bg-primary/90",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              "disabled:cursor-not-allowed disabled:opacity-70",
            )}
          >
            {checkMutation.isPending ? (
              <>
                <Loader2 className="size-4 animate-spin" strokeWidth={2} />
                Checking with backend…
              </>
            ) : (
              <>
                <CalendarSearch className="size-4" strokeWidth={1.75} />
                Check availability
              </>
            )}
          </button>

          {!isValid && Object.keys(errors).length === 0 && (
            <p className="mt-3 text-center text-[11px] text-muted-foreground">
              Complete every field to enable the availability check.
            </p>
          )}
        </form>

        {/* ---------------------------------------------------------- */}
        {/* Side panel: pre-flight status → summary → confirm          */}
        {/* ---------------------------------------------------------- */}
        <div className="flex flex-col gap-4">
          {checkMutation.isIdle && !bookMutation.isPending && (
            <EmptySidePanel />
          )}

          {checkMutation.isError && (
            <ApiErrorAlert
              error={checkMutation.error}
              onRetry={() => checkMutation.reset()}
              title="Availability check failed."
            />
          )}

          {checkMutation.isSuccess && availabilityData && (
            <AvailabilityStatus
              data={availabilityData}
              showAssistantHandoff={!isAvailable}
            />
          )}

          {isAvailable && (
            <>
              <BookingSummary
                patientName={watch("patient_name")}
                patientPhone={watch("patient_phone")}
                doctorId={doctorId}
                service={service}
                appointmentDate={date}
                appointmentTime={time}
                notes={watch("notes")}
              />

              {bookMutation.isError && (
                <ApiErrorAlert
                  error={bookMutation.error}
                  onRetry={() => bookMutation.reset()}
                  title="Booking failed."
                />
              )}

              <button
                type="button"
                onClick={handleConfirmBooking}
                disabled={bookMutation.isPending}
                className={cn(
                  "inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-md bg-status-confirmed px-5 py-2.5 text-sm font-medium text-status-confirmed-foreground",
                  "shadow-sm transition-colors hover:brightness-95",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  "disabled:cursor-not-allowed disabled:opacity-70",
                )}
              >
                {bookMutation.isPending ? (
                  <>
                    <Loader2 className="size-4 animate-spin" strokeWidth={2} />
                    Booking…
                  </>
                ) : (
                  <>
                    <ClipboardCheck className="size-4" strokeWidth={1.75} />
                    Confirm booking
                  </>
                )}
              </button>
              <p className="text-center text-[11px] text-muted-foreground">
                Clicking confirm calls POST /appointments. Nothing is
                committed to the workbook before then.
              </p>
            </>
          )}
        </div>
      </div>
    </AppShell>
  );
}

/* ------------------------------------------------------------------ */
/* Small local helpers                                                 */
/* ------------------------------------------------------------------ */

interface TextFieldOwnProps {
  id: string;
  label: string;
  icon: typeof UserRound;
  error?: string;
}
type TextFieldProps = TextFieldOwnProps &
  Omit<InputHTMLAttributes<HTMLInputElement>, "id">;

const TextField = forwardRef<HTMLInputElement, TextFieldProps>(
  function TextField(
    { id, label, icon: Icon, error, className, ...inputProps },
    ref,
  ) {
    return (
      <div className={cn("flex flex-col gap-1.5", className)}>
        <label
          htmlFor={id}
          className="text-xs font-medium uppercase tracking-widest text-muted-foreground"
        >
          {label}
        </label>
        <div className="relative">
          <Icon
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            strokeWidth={1.75}
            aria-hidden="true"
          />
          <input
            id={id}
            ref={ref}
            aria-invalid={!!error}
            aria-describedby={error ? `${id}-error` : undefined}
            className={cn(
              "min-h-[44px] w-full rounded-md border border-border bg-background pl-9 pr-3 py-2 text-sm text-foreground",
              "placeholder:text-muted-foreground",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              "disabled:cursor-not-allowed disabled:opacity-60",
              error && "border-destructive/60",
            )}
            {...inputProps}
          />
        </div>
        {error && (
          <p id={`${id}-error`} className="text-xs text-destructive">
            {error}
          </p>
        )}
      </div>
    );
  },
);

function EmptySidePanel() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center rounded-2xl border border-dashed border-border bg-card/50 p-8 text-center">
      <span
        aria-hidden="true"
        className="inline-flex size-11 items-center justify-center rounded-full bg-muted text-muted-foreground"
      >
        <CalendarSearch className="size-5" strokeWidth={1.75} />
      </span>
      <p className="mt-4 text-sm font-medium text-foreground">
        Two safe steps.
      </p>
      <ol className="mt-2 space-y-1 text-xs text-muted-foreground">
        <li>1. Check the slot with the backend.</li>
        <li>2. Review the summary and confirm.</li>
      </ol>
    </div>
  );
}
