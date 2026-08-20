/**
 * Wire-level types for the CareFlow AI FastAPI backend.
 *
 * Hand-mirrored 1:1 from the live OpenAPI schema at /openapi.json, not
 * from the docs. Field names, optionality, and enum values must match
 * the Pydantic schemas in `backend/app/api/schemas/`. If the backend
 * contract changes, update this file — never work around a drift here.
 *
 * Transport values stay as raw strings (ISO date / time / date-time)
 * so the client is never surprised by shape. Formatting is a UI
 * concern (see `lib/format.ts`), not a type concern.
 */

// -----------------------------------------------------------------------------
// Primitives — string aliases document intent without adding runtime cost.
// -----------------------------------------------------------------------------

/** ISO calendar date, e.g. "2026-08-16". */
export type IsoDate = string;

/**
 * ISO time. Backend REQUESTS accept "HH:MM" or "HH:MM:SS"; backend
 * RESPONSES always include seconds ("HH:MM:SS"). Kept as one alias so
 * the type never lies; callers use `formatTime()` for display.
 */
export type IsoTime = string;

/** ISO datetime with no timezone offset, e.g. "2026-08-16T10:00:00". */
export type IsoDateTime = string;

// -----------------------------------------------------------------------------
// Enums
// -----------------------------------------------------------------------------

/** Master Spec §11 — the six valid appointment statuses. Closed set. */
export const APPOINTMENT_STATUSES = [
  "Pending",
  "Confirmed",
  "Rejected",
  "Cancelled",
  "Completed",
  "NoShow",
] as const;

export type AppointmentStatus = (typeof APPOINTMENT_STATUSES)[number];

// -----------------------------------------------------------------------------
// Health — GET /health
// -----------------------------------------------------------------------------

/**
 * Backend returns a plain dict; no schema is registered in OpenAPI.
 * Shape verified from `backend/app/api/routes/health.py`.
 */
export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  environment: string;
}

// -----------------------------------------------------------------------------
// Chat — POST /chat  (API-001)
// -----------------------------------------------------------------------------

export interface ChatRequest {
  message: string;
  /** Accepted but not persisted server-side today — see supervisor.py. */
  session_id?: string | null;
  patient_phone?: string | null;
}

export interface ChatResponse {
  message: string;
  /**
   * Free string per the backend contract, but in practice always one
   * of a closed set the frontend can safely switch on.
   */
  intent: ChatIntent;
  /**
   * Structured tool payload when the agent successfully invoked one.
   * Kept intentionally loose — callers narrow via `intent` before
   * treating this as a specific shape (see `narrowChatData`).
   */
  data: Record<string, unknown> | null;
  requires_staff_review: boolean;
  request_id: string;
}

/**
 * Closed set of intents the current agent + supervisor can emit
 * (verified against `appointment_agent.py`, `supervisor.py`, and
 * `llm_provider.py`). If the backend grows a new intent, add it here
 * and add a card for it — do not fall through silently.
 */
export type ChatIntent =
  | "unsupported"
  | "needs_information"
  | "error"
  | "check_availability"
  | "find_alternative_slots"
  | "create_appointment"
  | "get_appointment"
  | "update_appointment"
  | "cancel_appointment"
  | "approve_appointment"
  | "reject_appointment";

// -----------------------------------------------------------------------------
// Availability — POST /appointments/check-availability  (API-002)
// -----------------------------------------------------------------------------

export interface AvailabilityRequest {
  doctor_id: string;
  appointment_date: IsoDate;
  appointment_time: IsoTime;
  service?: string | null;
}

export interface AvailabilityResponse {
  available: boolean;
  doctor_id: string;
  appointment_date: IsoDate;
  appointment_time: IsoTime;
  message: string;
}

/**
 * No public endpoint returns this today — it only appears inside
 * `ChatResponse.data` when the agent runs the `find_alternative_slots`
 * tool. Kept here so `data` can be narrowed by intent later.
 */
export interface AlternativeSlot {
  doctor_id: string;
  doctor_name: string;
  appointment_date: IsoDate;
  appointment_time: IsoTime;
}

export interface AlternativeSlotsResponse {
  requested_slot_available: boolean;
  alternatives: AlternativeSlot[];
}

// -----------------------------------------------------------------------------
// Appointments — /appointments/*  (API-003 through API-006)
// -----------------------------------------------------------------------------

export interface AppointmentCreate {
  patient_name: string;
  patient_phone: string;
  doctor_id: string;
  doctor_name: string;
  service: string;
  appointment_date: IsoDate;
  appointment_time: IsoTime;
  notes?: string | null;
}

export interface AppointmentUpdate {
  doctor_id?: string | null;
  doctor_name?: string | null;
  service?: string | null;
  appointment_date?: IsoDate | null;
  appointment_time?: IsoTime | null;
  notes?: string | null;
}

export interface AppointmentCancelRequest {
  reason?: string | null;
}

export interface AppointmentResponse {
  appointment_id: string;
  patient_name: string;
  patient_phone: string;
  doctor_id: string;
  doctor_name: string;
  service: string;
  appointment_date: IsoDate;
  appointment_time: IsoTime;
  status: AppointmentStatus;
  created_at: IsoDateTime;
  updated_at: IsoDateTime;
  /**
   * Not in OpenAPI `required`, so it may be `null` or omitted; kept
   * optional to match the wire shape.
   */
  notes?: string | null;
}

// -----------------------------------------------------------------------------
// Staff — /staff/appointments/{id}/{approve|reject}  (API-008 / API-009)
// -----------------------------------------------------------------------------

export interface StaffApprovalRequest {
  notes?: string | null;
  /** Placeholder demo-auth flag — see `backend/app/api/routes/staff.py`. */
  is_staff?: boolean;
  staff_id?: string | null;
}

export interface StaffRejectionRequest {
  /** Required, min length 3 (enforced server-side via Pydantic). */
  reason: string;
  is_staff?: boolean;
  staff_id?: string | null;
}

// -----------------------------------------------------------------------------
// Errors — FastAPI §14 envelope + FastAPI's own 422 shape
// -----------------------------------------------------------------------------

/** Documented business-error envelope (400/403/404/409/500). */
export interface ErrorResponse {
  error: ErrorDetail;
}

export interface ErrorDetail {
  code: ErrorCode;
  message: string;
  request_id: string;
  details: unknown | null;
}

/**
 * The complete error-code catalog wired up by the backend. Source:
 * `backend/app/api/routes/_tool_result_response.py::STATUS_BY_CODE`.
 * Unknown codes still parse (kept as string), but callers can rely on
 * this closed set for switch/case handling.
 */
export type ErrorCode =
  | "DOCTOR_NOT_FOUND"
  | "DOCTOR_INACTIVE"
  | "OUTSIDE_AVAILABILITY"
  | "INVALID_SLOT_TIME"
  | "SLOT_UNAVAILABLE"
  | "APPOINTMENT_NOT_FOUND"
  | "INVALID_APPOINTMENT_STATE"
  | "UNAUTHORIZED"
  | "REPOSITORY_ERROR"
  | "VALIDATION_ERROR"
  | (string & {});

/** FastAPI's own 422 shape — a separate error format from the envelope. */
export interface FastApiValidationError {
  detail: FastApiValidationIssue[];
}

export interface FastApiValidationIssue {
  loc: Array<string | number>;
  msg: string;
  type: string;
}
