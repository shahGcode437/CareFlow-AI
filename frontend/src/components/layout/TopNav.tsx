import { Link, useLocation } from "react-router-dom";
import { Stethoscope } from "lucide-react";
import { NAV_ITEMS, isActivePath } from "@/config/routes";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { cn } from "@/lib/utils";
import { MobileNav } from "@/components/layout/MobileNav";

/**
 * Desktop top navigation. The mobile hamburger + drawer live inside
 * `<MobileNav/>`, mounted here so both experiences share one row.
 */
export function TopNav() {
  const { pathname } = useLocation();

  return (
    <header
      className={cn(
        "sticky top-0 z-40 w-full border-b border-border",
        // Slight translucency + backdrop blur reads as premium without
        // shipping shadows or gradients.
        "bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70",
      )}
    >
      <div className="mx-auto flex h-16 max-w-6xl items-center gap-3 px-4 sm:px-6">
        <Link
          to="/"
          aria-label="CareFlow AI — home"
          className={cn(
            "flex items-center gap-2 rounded-md px-1 py-1 text-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
          )}
        >
          <span
            aria-hidden="true"
            className="inline-flex size-8 items-center justify-center rounded-md bg-primary text-primary-foreground"
          >
            <Stethoscope className="size-4.5" strokeWidth={2} />
          </span>
          <span className="flex flex-col leading-none">
            <span className="text-sm font-semibold tracking-tight">
              CareFlow AI
            </span>
            <span className="mt-0.5 text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
              Clinic front office
            </span>
          </span>
        </Link>

        {/* Desktop primary nav */}
        <nav
          aria-label="Primary"
          className="ml-6 hidden items-center gap-1 md:flex"
        >
          {NAV_ITEMS.map((item) => {
            const active = isActivePath(pathname, item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  active
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                )}
              >
                <item.icon className="size-4" strokeWidth={1.75} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-1">
          <ThemeToggle />
          <MobileNav />
        </div>
      </div>
    </header>
  );
}
