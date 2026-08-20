import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind class strings, resolving conflicting utilities so the
 * last one wins. The single helper every shadcn/ui primitive expects.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
