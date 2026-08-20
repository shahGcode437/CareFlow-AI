import { AppShell } from "@/components/layout/AppShell";
import { PageHeader } from "@/components/layout/PageHeader";
import { ChatWindow } from "@/components/chat/ChatWindow";

/**
 * `/assistant` — the AI Assistant experience.
 *
 * Kept intentionally thin: PageHeader for context + branding, then the
 * self-contained `<ChatWindow/>`. All state, API calls, and rendering
 * logic live inside the chat module.
 */
export default function AssistantPage() {
  return (
    <AppShell>
      <PageHeader
        eyebrow="AI Assistant"
        title="Chat with CareFlow"
        description="Natural-language appointment coordination. Powered by the CareFlow FastAPI backend — the assistant only invokes approved tools."
      />
      <div className="mt-6">
        <ChatWindow />
      </div>
    </AppShell>
  );
}
