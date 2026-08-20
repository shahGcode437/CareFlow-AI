import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Loader2 } from "lucide-react";

/**
 * Route-level code splitting.
 *
 * Every page is a separate `React.lazy` chunk so the initial bundle
 * only ships the router + shell code. The Suspense fallback below
 * carries the design-system feel while a chunk is fetched; in
 * practice on modern connections this is invisible after the first
 * navigation.
 */
const LandingPage = lazy(() => import("@/pages/LandingPage"));
const AssistantPage = lazy(() => import("@/pages/AssistantPage"));
const BookAppointmentPage = lazy(() => import("@/pages/BookAppointmentPage"));
const AvailabilityPage = lazy(() => import("@/pages/AvailabilityPage"));
const AppointmentsPage = lazy(() => import("@/pages/AppointmentsPage"));
const AppointmentDetailPage = lazy(
  () => import("@/pages/AppointmentDetailPage"),
);
const StaffPage = lazy(() => import("@/pages/StaffPage"));
const NotFoundPage = lazy(() => import("@/pages/NotFoundPage"));

function RouteFallback() {
  return (
    <div
      role="status"
      aria-live="polite"
      aria-label="Loading page"
      className="flex min-h-[60vh] items-center justify-center bg-background text-muted-foreground"
    >
      <Loader2 className="size-6 animate-spin" strokeWidth={2} aria-hidden="true" />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/assistant" element={<AssistantPage />} />
          <Route path="/book" element={<BookAppointmentPage />} />
          <Route path="/availability" element={<AvailabilityPage />} />
          <Route path="/appointments" element={<AppointmentsPage />} />
          <Route path="/appointments/:id" element={<AppointmentDetailPage />} />
          <Route path="/staff" element={<StaffPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
