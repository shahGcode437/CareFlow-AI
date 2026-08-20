import type { IsoDate, IsoTime } from "@/types/api";

/**
 * Small display helpers. Deliberately UI-facing — never used to
 * reshape data before sending it back to the backend. Business logic
 * (availability, conflicts, state transitions) lives server-side only.
 */

/**
 * Backend responses return time as "HH:MM:SS"; requests accept either
 * "HH:MM" or "HH:MM:SS". Trim the seconds when they're the trailing
 * `:00` so display and re-submission stay tidy.
 */
export function trimSeconds(time: IsoTime): string {
  if (/^\d{2}:\d{2}:\d{2}$/.test(time)) return time.slice(0, 5);
  return time;
}

/** "17:00:00" -> "5:00 PM". Falls back to the raw value if unparsable. */
export function formatTime(time: IsoTime): string {
  const m = /^(\d{2}):(\d{2})(?::\d{2})?$/.exec(time);
  if (!m) return time;
  const hh = Number(m[1]);
  const mm = m[2];
  const suffix = hh >= 12 ? "PM" : "AM";
  const hour12 = ((hh + 11) % 12) + 1;
  return `${hour12}:${mm} ${suffix}`;
}

/** "2026-08-16" -> "Sun, 16 Aug 2026". Falls back to the raw value. */
export function formatDate(date: IsoDate): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date);
  if (!m) return date;
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  if (Number.isNaN(d.getTime())) return date;
  return d.toLocaleDateString(undefined, {
    weekday: "short",
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}
