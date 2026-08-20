import { Link } from "react-router-dom";
import { Compass } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Generic "we couldn't find that" panel. Used by the 404 page for
 * unknown routes and by feature pages for a missing resource (e.g.
 * "Appointment APT-XYZ not found"). Kept as a component so both cases
 * feel the same.
 */
export function NotFoundState({
  title = "Page not found.",
  description = "That link doesn't lead anywhere in CareFlow AI.",
  homeHref = "/",
  className,
}: {
  title?: string;
  description?: string;
  homeHref?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "mx-auto flex max-w-md flex-col items-center rounded-lg border border-border bg-card px-6 py-10 text-center",
        className,
      )}
    >
      <span
        aria-hidden="true"
        className="mb-4 inline-flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground"
      >
        <Compass className="size-6" strokeWidth={1.75} />
      </span>
      <h2 className="text-lg font-semibold tracking-tight text-foreground">
        {title}
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      <Link
        to={homeHref}
        className={cn(
          "mt-5 inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground",
          "hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
        )}
      >
        Back to home
      </Link>
    </div>
  );
}
