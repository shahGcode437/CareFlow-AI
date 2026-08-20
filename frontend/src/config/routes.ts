import {
  CalendarClock,
  CalendarPlus,
  Search,
  ShieldCheck,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

/**
 * Single source of truth for the primary navigation.
 *
 * The Landing route (`/`) is intentionally NOT in this array — the
 * brand mark in `TopNav` links back to it, and duplicating it as a
 * regular nav pill would be visual noise.
 */

export interface NavItem {
  path: string;
  label: string;
  description: string;
  icon: LucideIcon;
}

export const NAV_ITEMS: readonly NavItem[] = [
  {
    path: "/assistant",
    label: "Assistant",
    description: "Book, reschedule, or ask in natural language.",
    icon: Sparkles,
  },
  {
    path: "/availability",
    label: "Availability",
    description: "Check a specific doctor, date, and time.",
    icon: CalendarClock,
  },
  {
    path: "/book",
    label: "Book",
    description: "Deterministic appointment request form.",
    icon: CalendarPlus,
  },
  {
    path: "/appointments",
    label: "Find appointment",
    description: "Look up an existing appointment by ID.",
    icon: Search,
  },
  {
    path: "/staff",
    label: "Staff",
    description: "Clinic staff console — demo mode.",
    icon: ShieldCheck,
  },
] as const;

/** Utility used by TopNav / MobileNav for active-route highlighting. */
export function isActivePath(currentPath: string, itemPath: string): boolean {
  if (itemPath === "/") return currentPath === "/";
  return currentPath === itemPath || currentPath.startsWith(`${itemPath}/`);
}
