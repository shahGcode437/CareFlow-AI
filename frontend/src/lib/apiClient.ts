/**
 * The one and only HTTP entry point for the CareFlow AI frontend.
 *
 * Every API module in `src/api/*` goes through `apiFetch`. Nothing else
 * calls `fetch()` directly. Consolidating here keeps three things
 * consistent across the app:
 *
 *   1. Base URL, headers, and per-request `X-Request-ID` propagation.
 *   2. Timeouts — a shorter default and a longer one for `/chat`,
 *      since the agent may sit inside a Groq LLM call for up to 15 s
 *      (see `backend/app/agents/llm_provider.py`).
 *   3. Error normalization. The backend uses TWO different error
 *      shapes — the documented `{ error: { code, message, ... } }`
 *      envelope for business/tool failures, and FastAPI's own
 *      `{ detail: [...] }` for 422 request-body validation. Both are
 *      collapsed into a single `ApiError` so UI code never branches
 *      on transport shape.
 */

import type {
  ErrorCode,
  ErrorResponse,
  FastApiValidationError,
  FastApiValidationIssue,
} from "@/types/api";

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

/**
 * Never hardcode a production URL. Read from Vite's typed env; fall
 * back to `http://localhost:8000` for local dev so `npm run dev`
 * works out of the box, matching `frontend/.env.example`.
 */
const BASE_URL: string =
  ((import.meta.env as ImportMetaEnv | undefined)?.VITE_API_BASE_URL as string | undefined)
    ?.replace(/\/+$/, "") ?? "http://localhost:8000";

/** Default timeout for deterministic endpoints (availability, CRUD). */
const DEFAULT_TIMEOUT_MS = 15_000;

/**
 * Longer budget for `/chat` — the backend may synchronously wait on a
 * 15 s Groq LLM call (see `GroqLLMProvider.timeout` = 15.0). Give the
 * frontend a 30 s ceiling so a healthy slow response isn't aborted.
 */
export const CHAT_TIMEOUT_MS = 30_000;

// ---------------------------------------------------------------------------
// Public error type — the ONLY error shape UI code should touch.
// ---------------------------------------------------------------------------

export type ApiErrorKind =
  | "network" // fetch itself failed / offline / DNS / CORS
  | "timeout" // AbortSignal.timeout fired
  | "validation" // FastAPI 422 body-validation
  | "business" // documented `{ error: { code, ... } }` envelope
  | "unknown"; // anything else (unparseable body, unexpected 5xx shape)

export interface ApiFieldError {
  /** Dotted path to the offending field, e.g. `"body.patient_name"`. */
  path: string;
  message: string;
  type: string;
}

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number;
  readonly code: ErrorCode;
  readonly requestId?: string;
  readonly fieldErrors?: ApiFieldError[];
  readonly details?: unknown;

  constructor(init: {
    kind: ApiErrorKind;
    status: number;
    code: ErrorCode;
    message: string;
    requestId?: string;
    fieldErrors?: ApiFieldError[];
    details?: unknown;
  }) {
    super(init.message);
    this.name = "ApiError";
    this.kind = init.kind;
    this.status = init.status;
    this.code = init.code;
    this.requestId = init.requestId;
    this.fieldErrors = init.fieldErrors;
    this.details = init.details;
  }
}

// ---------------------------------------------------------------------------
// Request-ID generation — small, dependency-free UUID v4
// ---------------------------------------------------------------------------

/**
 * `crypto.randomUUID` exists in every browser Vite targets and in
 * modern Node. The `webcrypto` fallback keeps SSR-style test runs
 * safe without pulling in the `uuid` package.
 */
function generateRequestId(): string {
  const g = globalThis as { crypto?: { randomUUID?: () => string } };
  if (g.crypto?.randomUUID) return g.crypto.randomUUID();
  // Extremely unlikely fallback — RFC-4122 v4 shape.
  const bytes = new Uint8Array(16);
  (g.crypto as unknown as Crypto).getRandomValues(bytes);
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

// ---------------------------------------------------------------------------
// Request options
// ---------------------------------------------------------------------------

export interface ApiFetchOptions<TBody> {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: TBody;
  /** Override the default timeout (ms). Chat uses `CHAT_TIMEOUT_MS`. */
  timeoutMs?: number;
  /** Optional caller-supplied request id; otherwise one is generated. */
  requestId?: string;
  /** Additional headers merged over the defaults. */
  headers?: Record<string, string>;
  /** Optional external AbortSignal — combined with the timeout signal. */
  signal?: AbortSignal;
}

// ---------------------------------------------------------------------------
// Error-body parsing — normalizes both backend shapes into ApiError
// ---------------------------------------------------------------------------

function isBusinessEnvelope(v: unknown): v is ErrorResponse {
  if (typeof v !== "object" || v === null) return false;
  const err = (v as { error?: unknown }).error;
  return (
    typeof err === "object" &&
    err !== null &&
    typeof (err as { code?: unknown }).code === "string" &&
    typeof (err as { message?: unknown }).message === "string"
  );
}

function isFastApiValidation(v: unknown): v is FastApiValidationError {
  if (typeof v !== "object" || v === null) return false;
  const detail = (v as { detail?: unknown }).detail;
  return Array.isArray(detail);
}

function toFieldErrors(detail: FastApiValidationIssue[]): ApiFieldError[] {
  return detail.map((d) => ({
    path: d.loc.map(String).join("."),
    message: d.msg,
    type: d.type,
  }));
}

async function parseErrorBody(response: Response, requestId: string): Promise<ApiError> {
  const status = response.status;
  const headerRequestId = response.headers.get("x-request-id") ?? requestId;

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // Non-JSON error body — fall through to "unknown" below.
  }

  if (isBusinessEnvelope(body)) {
    const err = body.error;
    return new ApiError({
      kind: "business",
      status,
      code: err.code,
      message: err.message,
      requestId: err.request_id || headerRequestId,
      details: err.details,
    });
  }

  if (isFastApiValidation(body)) {
    const fieldErrors = toFieldErrors(body.detail);
    return new ApiError({
      kind: "validation",
      status,
      code: "VALIDATION_ERROR",
      message:
        fieldErrors[0]?.message ??
        "Some fields were invalid. Please review and try again.",
      requestId: headerRequestId,
      fieldErrors,
    });
  }

  return new ApiError({
    kind: "unknown",
    status,
    code: "UNKNOWN_ERROR",
    message: `Request failed with status ${status}.`,
    requestId: headerRequestId,
    details: body,
  });
}

// ---------------------------------------------------------------------------
// Signal helper — merge timeout + optional external abort
// ---------------------------------------------------------------------------

function combineSignals(timeoutMs: number, external?: AbortSignal): AbortSignal {
  const timeout = AbortSignal.timeout(timeoutMs);
  if (!external) return timeout;
  // AbortSignal.any is widely supported in modern browsers and Node 20+.
  const anyFn = (AbortSignal as unknown as {
    any?: (signals: AbortSignal[]) => AbortSignal;
  }).any;
  if (anyFn) return anyFn([timeout, external]);
  // Fallback: manual composition.
  const controller = new AbortController();
  const onAbort = (reason: unknown) => controller.abort(reason);
  timeout.addEventListener("abort", () => onAbort(timeout.reason), { once: true });
  external.addEventListener("abort", () => onAbort(external.reason), { once: true });
  if (external.aborted) controller.abort(external.reason);
  return controller.signal;
}

// ---------------------------------------------------------------------------
// The single fetch wrapper
// ---------------------------------------------------------------------------

export async function apiFetch<TResponse, TBody = undefined>(
  path: string,
  options: ApiFetchOptions<TBody> = {},
): Promise<TResponse> {
  const {
    method = "GET",
    body,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    requestId = generateRequestId(),
    headers = {},
    signal,
  } = options;

  const url = `${BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
  const finalHeaders: Record<string, string> = {
    Accept: "application/json",
    "X-Request-ID": requestId,
    ...headers,
  };
  if (body !== undefined) {
    finalHeaders["Content-Type"] = "application/json";
  }

  let response: Response;
  try {
    response = await fetch(url, {
      method,
      headers: finalHeaders,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: combineSignals(timeoutMs, signal),
    });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "TimeoutError") {
      throw new ApiError({
        kind: "timeout",
        status: 0,
        code: "TIMEOUT",
        message: "The request took too long. Please try again.",
        requestId,
      });
    }
    if (cause instanceof DOMException && cause.name === "AbortError") {
      throw new ApiError({
        kind: "timeout",
        status: 0,
        code: "ABORTED",
        message: "The request was cancelled.",
        requestId,
      });
    }
    throw new ApiError({
      kind: "network",
      status: 0,
      code: "NETWORK_ERROR",
      message:
        "Couldn't reach the CareFlow AI backend. Check your connection and try again.",
      requestId,
      details: cause instanceof Error ? cause.message : String(cause),
    });
  }

  if (!response.ok) {
    throw await parseErrorBody(response, requestId);
  }

  // 204 or empty body — hand back an empty object cast to TResponse.
  if (response.status === 204) {
    return {} as TResponse;
  }

  try {
    return (await response.json()) as TResponse;
  } catch (cause) {
    throw new ApiError({
      kind: "unknown",
      status: response.status,
      code: "PARSE_ERROR",
      message: "The server returned a response we couldn't understand.",
      requestId: response.headers.get("x-request-id") ?? requestId,
      details: cause instanceof Error ? cause.message : String(cause),
    });
  }
}

/** Exposed for tests and dev diagnostics. */
export const _internals = { BASE_URL, DEFAULT_TIMEOUT_MS };
