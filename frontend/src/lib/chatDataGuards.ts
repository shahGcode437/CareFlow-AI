/**
 * Runtime type guards for the loosely-typed `ChatResponse.data` field.
 *
 * The backend types `data` as `object | null` in OpenAPI, but in
 * practice it's one of the shapes below depending on which tool the
 * Appointment Agent selected. These guards narrow the raw value so the
 * intent cards can render fields safely — no `any`, no manual key
 * lookups scattered across cards.
 */

import type {
  AlternativeSlot,
  AlternativeSlotsResponse,
  AppointmentResponse,
  AppointmentStatus,
  AvailabilityResponse,
} from "@/types/api";
import { APPOINTMENT_STATUSES } from "@/types/api";

function isObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function isString(v: unknown): v is string {
  return typeof v === "string";
}

function isBool(v: unknown): v is boolean {
  return typeof v === "boolean";
}

function isAppointmentStatus(v: unknown): v is AppointmentStatus {
  return isString(v) && (APPOINTMENT_STATUSES as readonly string[]).includes(v);
}

/** POST /appointments/check-availability response shape. */
export function isAvailabilityResponse(v: unknown): v is AvailabilityResponse {
  if (!isObject(v)) return false;
  return (
    isBool(v.available) &&
    isString(v.doctor_id) &&
    isString(v.appointment_date) &&
    isString(v.appointment_time) &&
    isString(v.message)
  );
}

/** Any /appointments/* success returns this shape (create/get/patch/cancel/approve/reject). */
export function isAppointmentResponse(v: unknown): v is AppointmentResponse {
  if (!isObject(v)) return false;
  return (
    isString(v.appointment_id) &&
    isString(v.patient_name) &&
    isString(v.patient_phone) &&
    isString(v.doctor_id) &&
    isString(v.doctor_name) &&
    isString(v.service) &&
    isString(v.appointment_date) &&
    isString(v.appointment_time) &&
    isAppointmentStatus(v.status) &&
    isString(v.created_at) &&
    isString(v.updated_at)
  );
}

/** Shape produced by the `find_alternative_slots` tool. */
export function isAlternativeSlotsResponse(
  v: unknown,
): v is AlternativeSlotsResponse {
  if (!isObject(v)) return false;
  if (!isBool(v.requested_slot_available)) return false;
  if (!Array.isArray(v.alternatives)) return false;
  return v.alternatives.every((slot): slot is AlternativeSlot => {
    return (
      isObject(slot) &&
      isString(slot.doctor_id) &&
      isString(slot.doctor_name) &&
      isString(slot.appointment_date) &&
      isString(slot.appointment_time)
    );
  });
}
