import { BrowserRouter, Route, Routes } from "react-router-dom";
import LandingPage from "@/pages/LandingPage";
import AssistantPage from "@/pages/AssistantPage";
import BookAppointmentPage from "@/pages/BookAppointmentPage";
import AvailabilityPage from "@/pages/AvailabilityPage";
import AppointmentsPage from "@/pages/AppointmentsPage";
import AppointmentDetailPage from "@/pages/AppointmentDetailPage";
import StaffPage from "@/pages/StaffPage";
import NotFoundPage from "@/pages/NotFoundPage";

/**
 * Route table for CareFlow AI. Kept in one place — the primary
 * navigation source of truth for the shell lives in
 * `src/config/routes.ts`; this file only owns URL → component wiring.
 */
export default function App() {
  return (
    <BrowserRouter>
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
    </BrowserRouter>
  );
}
