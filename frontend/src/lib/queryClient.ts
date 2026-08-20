import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "@/lib/apiClient";

/**
 * Single QueryClient for the app. Config choices:
 *
 * - `retry`: never retry `business` or `validation` failures — those
 *   won't get better with another attempt. Retry once on network /
 *   timeout so a flaky Excel-write blip doesn't bubble straight up.
 * - `staleTime`: 30 s. Reads are cheap; short freshness window keeps
 *   the UI honest without hammering the backend.
 * - `refetchOnWindowFocus`: off. Nothing here is time-critical, and
 *   the Excel store won't be edited out of band during a demo.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        if (error instanceof ApiError) {
          if (error.kind === "network" || error.kind === "timeout") {
            return failureCount < 1;
          }
          return false;
        }
        return failureCount < 1;
      },
    },
    mutations: {
      retry: false,
    },
  },
});
