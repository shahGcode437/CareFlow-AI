import { apiFetch } from "@/lib/apiClient";
import type {
  AppointmentCancelRequest,
  AppointmentCreate,
  AppointmentResponse,
  AppointmentUpdate,
  AvailabilityRequest,
  AvailabilityResponse,
} from "@/types/api";

/** POST /appointments/check-availability — API-002. */
export function checkAvailability(
  body: AvailabilityRequest,
  signal?: AbortSignal,
): Promise<AvailabilityResponse> {
  return apiFetch<AvailabilityResponse, AvailabilityRequest>(
    "/appointments/check-availability",
    { method: "POST", body, signal },
  );
}

/** GET /appointments/{id} — API-003. */
export function getAppointment(
  appointmentId: string,
  signal?: AbortSignal,
): Promise<AppointmentResponse> {
  return apiFetch<AppointmentResponse>(
    `/appointments/${encodeURIComponent(appointmentId)}`,
    { signal },
  );
}

/** POST /appointments — API-004. */
export function createAppointment(
  body: AppointmentCreate,
  signal?: AbortSignal,
): Promise<AppointmentResponse> {
  return apiFetch<AppointmentResponse, AppointmentCreate>("/appointments", {
    method: "POST",
    body,
    signal,
  });
}

/** PATCH /appointments/{id} — API-005. */
export function updateAppointment(
  appointmentId: string,
  body: AppointmentUpdate,
  signal?: AbortSignal,
): Promise<AppointmentResponse> {
  return apiFetch<AppointmentResponse, AppointmentUpdate>(
    `/appointments/${encodeURIComponent(appointmentId)}`,
    { method: "PATCH", body, signal },
  );
}

/** POST /appointments/{id}/cancel — API-006. Always a status transition. */
export function cancelAppointment(
  appointmentId: string,
  body: AppointmentCancelRequest = {},
  signal?: AbortSignal,
): Promise<AppointmentResponse> {
  return apiFetch<AppointmentResponse, AppointmentCancelRequest>(
    `/appointments/${encodeURIComponent(appointmentId)}/cancel`,
    { method: "POST", body, signal },
  );
}
