import type { ChatIntent } from "@/types/api";
import {
  isAlternativeSlotsResponse,
  isAppointmentResponse,
  isAvailabilityResponse,
} from "@/lib/chatDataGuards";
import { AvailabilityResultCard } from "./AvailabilityResultCard";
import { AlternativeSlotsCard } from "./AlternativeSlotsCard";
import { AppointmentResultCard } from "./AppointmentResultCard";
import { NeedsInfoCard } from "./NeedsInfoCard";
import { UnsupportedCard } from "./UnsupportedCard";

/**
 * Central intent → card mapping. Always narrows `data` with a runtime
 * guard before rendering a strongly-typed card. If the guard fails
 * (unexpected shape from a future backend change), nothing is
 * rendered under the assistant bubble — the text remains the source
 * of truth.
 *
 * The router never displays raw JSON.
 */
export function IntentCardRouter({
  intent,
  data,
  originalUserMessage,
  onUseSlot,
  onRephrase,
}: {
  intent: ChatIntent;
  data: Record<string, unknown> | null;
  originalUserMessage: string | null;
  onUseSlot?: (partial: string) => void;
  onRephrase?: (text: string) => void;
}) {
  switch (intent) {
    case "check_availability":
      return isAvailabilityResponse(data) ? (
        <AvailabilityResultCard data={data} />
      ) : null;

    case "find_alternative_slots":
      return isAlternativeSlotsResponse(data) ? (
        <AlternativeSlotsCard data={data} onUseSlot={onUseSlot} />
      ) : null;

    case "create_appointment":
    case "get_appointment":
    case "update_appointment":
    case "cancel_appointment":
    case "approve_appointment":
    case "reject_appointment":
      return isAppointmentResponse(data) ? (
        <AppointmentResultCard data={data} />
      ) : null;

    case "needs_information":
      return (
        <NeedsInfoCard
          originalMessage={originalUserMessage}
          onRephrase={onRephrase ?? (() => {})}
        />
      );

    case "unsupported":
      return <UnsupportedCard tone="unsupported" />;

    case "error":
      return <UnsupportedCard tone="error" />;

    default:
      // Unknown future intent — silently omit the card; the assistant
      // text will still render normally in the parent bubble.
      return null;
  }
}
