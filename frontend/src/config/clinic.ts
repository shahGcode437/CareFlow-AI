/**
 * ─────────────────────────────────────────────────────────────────────
 * DEMO / SEED CONFIGURATION
 * ─────────────────────────────────────────────────────────────────────
 *
 * The CareFlow backend deliberately does NOT expose a doctor-list
 * endpoint yet (Master Spec §18 leaves it out of the MVP API; the
 * workbook is the only source of truth). Rather than scatter DOC-001
 * and DOC-002 across form components, we consolidate the currently-
 * shipped seed doctors and their services here.
 *
 * This file is a PRESENTATION-LAYER FALLBACK ONLY. The backend
 * remains authoritative — every action is still routed through the
 * FastAPI endpoints and will fail correctly if these values drift
 * from the workbook. When the backend eventually grows a
 * `GET /doctors` endpoint, replace the constant below with a fetch
 * and delete the DEMO markers.
 *
 * Values below are copied from `backend/data/clinic_appointments_MVP_template.xlsx`
 * — Doctors sheet + Availability sheet.
 */

export interface DemoDoctor {
  id: string;
  name: string;
  specialty: string;
  services: readonly string[];
  /** Days of week the doctor has ANY availability in the seed data. */
  availableDays: readonly string[];
  /** Availability window, per seed data. */
  hours: {
    start: string; // "HH:MM"
    end: string; // "HH:MM"
    slotMinutes: number;
  };
}

export const DEMO_DOCTORS: readonly DemoDoctor[] = [
  {
    id: "DOC-001",
    name: "Dr. Ahmed",
    specialty: "General Medicine",
    services: ["General Consultation", "Follow-up Visit"],
    availableDays: ["Sunday"],
    hours: { start: "16:00", end: "20:00", slotMinutes: 30 },
  },
  {
    id: "DOC-002",
    name: "Dr. Sara",
    specialty: "Dermatology",
    services: ["Dermatology Consultation", "Skin Assessment"],
    availableDays: ["Sunday"],
    hours: { start: "17:00", end: "20:00", slotMinutes: 30 },
  },
] as const;

/** Convenience lookup used by the shared components. */
export function findDemoDoctor(doctorId: string): DemoDoctor | undefined {
  return DEMO_DOCTORS.find((d) => d.id === doctorId);
}

/**
 * Full day names as JavaScript's `Date.prototype.toLocaleDateString`
 * returns them, so we can cheaply compare a picked date's weekday
 * against a doctor's `availableDays` list.
 */
export const WEEKDAY_NAMES = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
] as const;

export function weekdayName(isoDate: string): string | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(isoDate);
  if (!m) return null;
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  if (Number.isNaN(d.getTime())) return null;
  return WEEKDAY_NAMES[d.getDay()] ?? null;
}
