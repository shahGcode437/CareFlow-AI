import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "@/components/theme/ThemeProvider";
import { cn } from "@/lib/utils";

/**
 * Single button that cycles light → dark → system. Icon reflects the
 * ACTIVE mode (not the resolved theme) so the user always sees what
 * they'll get on the next click, and the `aria-label` says the same.
 */
export function ThemeToggle({ className }: { className?: string }) {
  const { mode, cycle } = useTheme();

  const { Icon, label } =
    mode === "light"
      ? { Icon: Sun, label: "Theme: light. Switch to dark." }
      : mode === "dark"
        ? { Icon: Moon, label: "Theme: dark. Switch to system." }
        : { Icon: Monitor, label: "Theme: system. Switch to light." };

  return (
    <button
      type="button"
      onClick={cycle}
      aria-label={label}
      title={label}
      className={cn(
        "inline-flex size-11 items-center justify-center rounded-md border border-transparent",
        "text-muted-foreground transition-colors hover:bg-muted hover:text-foreground",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        className,
      )}
    >
      <Icon className="size-5" strokeWidth={1.75} />
    </button>
  );
}
