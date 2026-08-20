import { apiFetch } from "@/lib/apiClient";
import type {
  AppointmentResponse,
  StaffApprovalRequest,
  StaffRejectionRequest,
} from "@/types/api";

/**
 * POST /staff/appointments/{id}/approve — API-008.
 *
 * The backend has no real authentication yet; `is_staff` / `staff_id`
 * are placeholder fields the caller asserts. Do not treat this as a
 * secured operation on the frontend either — the staff console must
 * display an unambiguous "demo mode" banner (Phase 8.8).
 */
export function approveAppointment(
  appointmentId: string,
  body: StaffApprovalRequest = {},
  signal?: AbortSignal,
): Promise<AppointmentResponse> {
  return apiFetch<AppointmentResponse, StaffApprovalRequest>(
    `/staff/appointments/${encodeURIComponent(appointmentId)}/approve`,
    { method: "POST", body, signal },
  );
}

/** POST /staff/appointments/{id}/reject — API-009. Reason is required (min 3). */
export function rejectAppointment(
  appointmentId: string,
  body: StaffRejectionRequest,
  signal?: AbortSignal,
): Promise<AppointmentResponse> {
  return apiFetch<AppointmentResponse, StaffRejectionRequest>(
    `/staff/appointments/${encodeURIComponent(appointmentId)}/reject`,
    { method: "POST", body, signal },
  );
}
