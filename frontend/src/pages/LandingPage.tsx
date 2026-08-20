import { Link } from "react-router-dom";
import {
  ArrowRight,
  CalendarClock,
  CalendarPlus,
  CheckCircle2,
  MessageSquareText,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  type LucideIcon,
} from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { HeroPreviewCard } from "@/components/landing/HeroPreviewCard";
import { AssistantPreview } from "@/components/landing/AssistantPreview";
import { cn } from "@/lib/utils";

/**
 * Premium clinical landing page.
 *
 *   1. Hero — clinical grid backdrop, headline, dual CTAs
 *      ("Book an Appointment" primary, "Talk to AI Assistant"
 *      secondary), and a right-side static product preview.
 *   2. Trust strip — four capability lines, honestly limited to
 *      what CareFlow actually ships.
 *   3. How CareFlow works — three-step Ask → Coordinate → Confirm
 *      flow, with a subtle connector on desktop.
 *   4. Core features — four polished cards linking to the real
 *      feature routes.
 *   5. AI Assistant preview — larger mid-page static conversation.
 *   6. Final CTA — one-line hook plus the same two CTAs.
 *
 * Nothing here fabricates stats, testimonials, hospital partnerships,
 * or medical claims. Both preview panels are marked "Product preview".
 */
export default function LandingPage() {
  return (
    <AppShell wide>
      <Hero />
      <TrustStrip />
      <HowItWorks />
      <CoreFeatures />
      <AssistantPreview />
      <FinalCta />
    </AppShell>
  );
}

/* ------------------------------------------------------------------ */
/* 1. Hero                                                             */
/* ------------------------------------------------------------------ */

function Hero() {
  return (
    <section
      aria-labelledby="landing-hero-title"
      className="relative overflow-hidden border-b border-border bg-surface"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-clinical-grid opacity-70"
      />

      <div className="relative mx-auto grid max-w-6xl gap-10 px-4 py-16 sm:px-6 md:grid-cols-[3fr_2fr] md:py-24">
        <div className="animate-fade-in-up">
          <div className="inline-flex items-center gap-2 rounded-full border border-border bg-background/70 px-3 py-1 text-xs font-medium text-muted-foreground backdrop-blur">
            <Stethoscope
              className="size-3.5 text-primary"
              strokeWidth={2}
              aria-hidden="true"
            />
            AI-Powered Clinic Coordination
          </div>

          <h1
            id="landing-hero-title"
            className="mt-5 text-4xl font-semibold tracking-tight text-foreground sm:text-5xl md:text-6xl"
          >
            Healthcare appointments,{" "}
            <span className="relative inline-block text-primary">
              simplified by intelligence
              <span
                aria-hidden="true"
                className="absolute inset-x-0 -bottom-1 h-[3px] rounded-full bg-primary-soft"
              />
            </span>
            .
          </h1>

          <p className="mt-5 max-w-xl text-base text-muted-foreground sm:text-lg">
            CareFlow AI helps patients find availability, book appointments,
            and manage their visits through a simple AI-powered experience.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              to="/book"
              className={cn(
                "inline-flex items-center gap-2 rounded-md bg-primary px-5 py-3 text-sm font-medium text-primary-foreground",
                "shadow-sm transition-colors hover:bg-primary/90",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              )}
            >
              <CalendarPlus className="size-4" strokeWidth={1.75} />
              Book an Appointment
            </Link>
            <Link
              to="/assistant"
              className={cn(
                "inline-flex items-center gap-2 rounded-md border border-border bg-background/70 px-5 py-3 text-sm font-medium text-foreground backdrop-blur",
                "transition-colors hover:bg-muted",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
              )}
            >
              <Sparkles className="size-4" strokeWidth={1.75} />
              Talk to AI Assistant
            </Link>
          </div>

          <p className="mt-5 flex items-center gap-2 text-xs text-muted-foreground">
            <span
              aria-hidden="true"
              className="inline-block size-1.5 rounded-full bg-primary"
            />
            Demo data only · Excel-backed appointment store · Staff review
            preserved
          </p>
        </div>

        <div className="md:pl-4">
          <HeroPreviewCard />
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* 2. Trust strip                                                      */
/* ------------------------------------------------------------------ */

const TRUST_ITEMS: { label: string; detail: string }[] = [
  {
    label: "Smart appointment assistance",
    detail: "One conversational entry point",
  },
  {
    label: "Real-time availability checking",
    detail: "Doctor, date, and slot validation",
  },
  {
    label: "Staff review workflow",
    detail: "Approve or reject pending requests",
  },
  {
    label: "Simple patient experience",
    detail: "Plain-language messages",
  },
];

function TrustStrip() {
  return (
    <section
      aria-label="Core capabilities"
      className="border-b border-border bg-background"
    >
      <div className="mx-auto grid max-w-6xl grid-cols-2 gap-6 px-4 py-8 sm:px-6 md:grid-cols-4">
        {TRUST_ITEMS.map((item, i) => (
          <div
            key={item.label}
            className={cn(
              "flex items-start gap-3 animate-fade-in",
              i === 1 && "delay-75",
              i === 2 && "delay-150",
              i === 3 && "delay-300",
            )}
          >
            <span
              aria-hidden="true"
              className="mt-0.5 inline-flex size-8 items-center justify-center rounded-md bg-primary-soft text-primary-soft-foreground"
            >
              <CheckCircle2 className="size-4" strokeWidth={2} />
            </span>
            <div className="min-w-0">
              <div className="text-sm font-medium text-foreground">
                {item.label}
              </div>
              <div className="text-xs text-muted-foreground">{item.detail}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* 3. How CareFlow works                                              */
/* ------------------------------------------------------------------ */

interface Step {
  number: string;
  icon: LucideIcon;
  title: string;
  body: string;
}

const STEPS: Step[] = [
  {
    number: "01",
    icon: MessageSquareText,
    title: "Ask",
    body: "The patient tells CareFlow what they need — availability, a new appointment, a reschedule, or a cancellation.",
  },
  {
    number: "02",
    icon: CalendarClock,
    title: "Coordinate",
    body: "The AI checks appointment availability and follows the clinic workflow through deterministic tools and services.",
  },
  {
    number: "03",
    icon: ShieldCheck,
    title: "Confirm",
    body: "The appointment is created and staff review is handled whenever the clinic policy requires it.",
  },
];

function HowItWorks() {
  return (
    <section
      aria-labelledby="landing-how-it-works"
      className="border-b border-border bg-surface"
    >
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <div className="max-w-2xl">
          <div className="text-xs font-medium uppercase tracking-widest text-primary">
            How CareFlow works
          </div>
          <h2
            id="landing-how-it-works"
            className="mt-2 text-2xl font-semibold tracking-tight text-foreground sm:text-3xl"
          >
            One conversation. Three deliberate steps.
          </h2>
          <p className="mt-3 text-sm text-muted-foreground sm:text-base">
            The Supervisor routes intent, the Appointment Agent selects the
            correct tool, and the Service enforces every business rule.
          </p>
        </div>

        <ol className="relative mt-10 grid gap-4 md:grid-cols-3">
          {/* Desktop connector — a thin line at card-icon height that
              visually threads the three steps together. Hidden on
              mobile, where the flow is naturally vertical. */}
          <div
            aria-hidden="true"
            className="pointer-events-none absolute left-6 right-6 top-[68px] hidden h-px bg-border md:block"
          />

          {STEPS.map((step, i) => (
            <li key={step.number} className="relative">
              <div
                className={cn(
                  "flex h-full flex-col rounded-2xl border border-border bg-card p-6",
                  "hover-lift hover:border-primary/40",
                  "animate-fade-in-up",
                  i === 1 && "delay-150",
                  i === 2 && "delay-300",
                )}
              >
                <span
                  aria-hidden="true"
                  className="relative z-10 inline-flex size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground"
                >
                  <step.icon className="size-5" strokeWidth={1.75} />
                </span>
                <div className="mt-5 text-xs font-medium uppercase tracking-widest text-muted-foreground">
                  {step.number} — {step.title}
                </div>
                <div className="mt-1 text-base font-semibold tracking-tight text-foreground">
                  {stepHeadline(step.title)}
                </div>
                <p className="mt-2 text-sm text-muted-foreground">
                  {step.body}
                </p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function stepHeadline(title: string): string {
  if (title === "Ask") return "Patient describes the need.";
  if (title === "Coordinate") return "AI checks the clinic workflow.";
  return "Staff review preserves control.";
}

/* ------------------------------------------------------------------ */
/* 4. Core features                                                    */
/* ------------------------------------------------------------------ */

interface Feature {
  icon: LucideIcon;
  title: string;
  body: string;
  href: string;
}

const FEATURES: Feature[] = [
  {
    icon: Sparkles,
    title: "AI Appointment Assistant",
    body: "A conversational entry point that routes patient intent to the correct approved tool — no fabricated availability, ever.",
    href: "/assistant",
  },
  {
    icon: CalendarClock,
    title: "Availability Checking",
    body: "Validate a specific doctor, date, and time against configured clinic hours and existing bookings.",
    href: "/availability",
  },
  {
    icon: CalendarPlus,
    title: "Appointment Management",
    body: "Book, reschedule, or cancel — every mutation goes through the deterministic Appointment Service.",
    href: "/appointments",
  },
  {
    icon: ShieldCheck,
    title: "Staff Review Workflow",
    body: "Pending requests wait for a staff member to approve or reject with a reason. Statuses are preserved.",
    href: "/staff",
  },
];

function CoreFeatures() {
  return (
    <section
      aria-labelledby="landing-core-features"
      className="border-b border-border bg-background"
    >
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div className="max-w-2xl">
            <div className="text-xs font-medium uppercase tracking-widest text-primary">
              Core features
            </div>
            <h2
              id="landing-core-features"
              className="mt-2 text-2xl font-semibold tracking-tight text-foreground sm:text-3xl"
            >
              Everything a clinic front office actually needs.
            </h2>
          </div>
          <p className="max-w-md text-sm text-muted-foreground">
            Every card describes real functionality wired up to the CareFlow
            FastAPI backend.
          </p>
        </div>

        <ul className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((feature, i) => (
            <li key={feature.href}>
              <Link
                to={feature.href}
                className={cn(
                  "group flex h-full flex-col rounded-2xl border border-border bg-card p-6",
                  "hover-lift hover:border-primary/40",
                  "animate-fade-in-up",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                  i === 1 && "delay-75",
                  i === 2 && "delay-150",
                  i === 3 && "delay-300",
                )}
              >
                <span
                  aria-hidden="true"
                  className={cn(
                    "inline-flex size-10 items-center justify-center rounded-lg bg-primary-soft text-primary",
                    "transition-colors group-hover:bg-primary group-hover:text-primary-foreground",
                  )}
                >
                  <feature.icon className="size-5" strokeWidth={1.75} />
                </span>
                <div className="mt-5 flex items-center gap-1 text-base font-semibold tracking-tight text-foreground">
                  {feature.title}
                  <ArrowRight
                    className="size-4 -translate-x-1 text-muted-foreground opacity-0 transition-all group-hover:translate-x-0 group-hover:opacity-100"
                    strokeWidth={2}
                  />
                </div>
                <p className="mt-1.5 text-sm text-muted-foreground">
                  {feature.body}
                </p>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* 6. Final CTA                                                        */
/* ------------------------------------------------------------------ */

function FinalCta() {
  return (
    <section
      aria-labelledby="landing-final-cta"
      className="bg-background"
    >
      <div className="mx-auto max-w-4xl px-4 py-16 text-center sm:px-6 sm:py-20">
        <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-muted-foreground">
          <span
            aria-hidden="true"
            className="inline-block size-1.5 rounded-full bg-primary"
          />
          Ready when you are
        </div>
        <h2
          id="landing-final-cta"
          className="mt-4 text-3xl font-semibold tracking-tight text-foreground sm:text-4xl"
        >
          Ready to simplify your next appointment?
        </h2>
        <p className="mx-auto mt-3 max-w-xl text-sm text-muted-foreground sm:text-base">
          Start with the form or let the assistant do the talking. Every path
          uses the same deterministic backend.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link
            to="/book"
            className={cn(
              "inline-flex items-center gap-2 rounded-md bg-primary px-5 py-3 text-sm font-medium text-primary-foreground",
              "shadow-sm transition-colors hover:bg-primary/90",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
            )}
          >
            <CalendarPlus className="size-4" strokeWidth={1.75} />
            Book Appointment
          </Link>
          <Link
            to="/assistant"
            className={cn(
              "inline-flex items-center gap-2 rounded-md border border-border bg-card px-5 py-3 text-sm font-medium text-foreground",
              "transition-colors hover:bg-muted",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
            )}
          >
            <Sparkles className="size-4" strokeWidth={1.75} />
            Try AI Assistant
          </Link>
        </div>
      </div>
    </section>
  );
}
