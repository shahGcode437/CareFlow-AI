import type { ReactNode } from "react";
import { TopNav } from "@/components/layout/TopNav";
import { Footer } from "@/components/layout/Footer";
import { cn } from "@/lib/utils";

/**
 * Application shell used by every page.
 *
 * Layout rules:
 *   - Sticky `TopNav` with translucent background.
 *   - Main content sits in a max-width column with generous side gutter.
 *   - Landing (or any page that wants a full-bleed hero) can opt out
 *     of the content max-width by passing `wide`.
 *   - Skip link jumps straight to the main region — important for
 *     keyboard and screen-reader users on every route.
 */
export function AppShell({
  children,
  wide = false,
}: {
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <div className="flex min-h-full flex-col bg-background text-foreground">
      <a
        href="#main"
        className={cn(
          "sr-only focus:not-sr-only",
          "focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md",
          "focus:bg-card focus:px-3 focus:py-2 focus:text-sm focus:font-medium focus:text-foreground",
          "focus:shadow focus:outline-none focus:ring-2 focus:ring-ring",
        )}
      >
        Skip to main content
      </a>

      <TopNav />

      <main
        id="main"
        className={cn(
          "flex-1",
          wide ? "" : "mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 sm:py-10",
        )}
      >
        {children}
      </main>

      <Footer />
    </div>
  );
}
