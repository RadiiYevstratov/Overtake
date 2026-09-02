/**
 * The single seam between the web app and the Overtake API.
 *
 * Server components call the API directly over the internal URL; the browser
 * calls it through the same-origin `/api/v1` rewrite, so the session cookie is
 * first-party and the double-submit CSRF token works without exemptions.
 */

export const API_PREFIX = "/api/v1";

const INTERNAL_ORIGIN = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly errorId?: string,
    readonly extra: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** 402 means the caller is signed in but their plan does not cover this. */
  get isUpgradeRequired() {
    return this.status === 402;
  }
  get isAuthRequired() {
    return this.status === 401;
  }
  get isNotFound() {
    return this.status === 404;
  }
  /** 425 Too Early: the data exists, the simulation has not finished. */
  get isNotSimulatedYet() {
    return this.status === 425;
  }
}

type Json = Record<string, unknown>;

async function toError(response: Response): Promise<ApiError> {
  let body: Json = {};
  try {
    body = (await response.json()) as Json;
  } catch {
    // A non-JSON error body means something upstream of the API failed.
  }
  const error = (body.error ?? {}) as Json;
  return new ApiError(
    response.status,
    typeof error.code === "string" ? error.code : "UNKNOWN",
    typeof error.message === "string"
      ? error.message
      : "Something went wrong. Please try again.",
    typeof error.error_id === "string" ? error.error_id : undefined,
    error,
  );
}

/**
 * Server-side fetch. Used by React Server Components, so it must never throw
 * for an expected condition the page can render — callers decide.
 */
export async function serverFetch<T>(
  path: string,
  init: RequestInit & { revalidate?: number } = {},
): Promise<T> {
  const { revalidate, ...rest } = init;
  const headers = new Headers(rest.headers);
  headers.set("Accept", "application/json");

  // Forward the visitor's cookies so authenticated pages render server-side.
  if (typeof window === "undefined") {
    const { cookies } = await import("next/headers");
    const jar = await cookies();
    const cookieHeader = jar
      .getAll()
      .map((c) => `${c.name}=${c.value}`)
      .join("; ");
    if (cookieHeader) headers.set("Cookie", cookieHeader);
  }

  const response = await fetch(`${INTERNAL_ORIGIN}${API_PREFIX}${path}`, {
    ...rest,
    headers,
    // Authenticated responses are never cached; public pages opt in explicitly.
    cache: revalidate === undefined ? "no-store" : undefined,
    next: revalidate === undefined ? undefined : { revalidate },
  });

  if (!response.ok) throw await toError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** Server fetch that returns null instead of throwing on an expected miss. */
export async function serverFetchOrNull<T>(
  path: string,
  init?: RequestInit & { revalidate?: number },
): Promise<T | null> {
  try {
    return await serverFetch<T>(path, init);
  } catch (error) {
    if (error instanceof ApiError) return null;
    throw error;
  }
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match?.[1] ? decodeURIComponent(match[1]) : null;
}

/**
 * Browser fetch. Attaches the CSRF token on every mutating request, which is
 * the client half of the double-submit pattern.
 */
export async function clientFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrf = readCookie("overtake_csrf");
    if (csrf) headers.set("X-Overtake-CSRF", csrf);
  }

  const response = await fetch(`${API_PREFIX}${path}`, {
    ...init,
    headers,
    credentials: "same-origin",
  });

  if (!response.ok) throw await toError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** Fire-and-forget analytics. Never blocks a user action, never throws. */
export function track(name: string, props: Record<string, unknown> = {}): void {
  if (typeof window === "undefined") return;
  void clientFetch("/analytics/event", {
    method: "POST",
    body: JSON.stringify({ name, props }),
  }).catch(() => {
    /* Analytics must never break the product. */
  });
}
