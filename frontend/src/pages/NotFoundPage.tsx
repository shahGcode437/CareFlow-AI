import { useLocation } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { NotFoundState } from "@/components/feedback/NotFoundState";

export default function NotFoundPage() {
  const { pathname } = useLocation();
  return (
    <AppShell>
      <div className="py-16">
        <NotFoundState
          title="Page not found."
          description={`No CareFlow AI screen matches "${pathname}". Head back home to keep going.`}
        />
      </div>
    </AppShell>
  );
}
