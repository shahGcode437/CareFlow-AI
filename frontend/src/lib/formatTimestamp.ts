/**
 * Compact timestamp for chat bubbles.
 *
 *   < 45 s      → "Just now"
 *   < 60 min    → "5 min ago"
 *   same day    → "5:43 PM"
 *   older       → "16 Aug · 5:43 PM"
 */
export function formatRelativeTime(timestamp: number, now = Date.now()): string {
  const deltaSec = Math.max(0, Math.floor((now - timestamp) / 1000));
  if (deltaSec < 45) return "Just now";
  if (deltaSec < 3600) {
    const min = Math.floor(deltaSec / 60);
    return `${min} min ago`;
  }
  const then = new Date(timestamp);
  const nowDate = new Date(now);
  const sameDay =
    then.getFullYear() === nowDate.getFullYear() &&
    then.getMonth() === nowDate.getMonth() &&
    then.getDate() === nowDate.getDate();
  const time = then.toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
  if (sameDay) return time;
  const day = then.toLocaleDateString(undefined, { day: "numeric", month: "short" });
  return `${day} · ${time}`;
}
