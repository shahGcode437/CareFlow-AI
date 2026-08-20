import { apiFetch } from "@/lib/apiClient";
import type { HealthResponse } from "@/types/api";

/** Backend liveness probe. Used by the connectivity indicator. */
export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health", { signal });
}
