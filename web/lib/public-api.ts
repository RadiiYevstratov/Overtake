/**
 * Public, cacheable API data — player, club, gameweek and comparison pages,
 * the season meta and the sitemap's index. Server-only: client components
 * import `lib/api`, never this module.
 */

import { unstable_cache } from "next/cache";
import { cache } from "react";

import {
  API_PREFIX,
  ApiError,
  INTERNAL_ORIGIN,
  PROXY_CLIENT_IP_HEADER,
  PROXY_SECRET_HEADER,
  toError,
} from "@/lib/api";

const PUBLIC_TIMEOUT_MS = 10_000;
/** A rate limit that clears this soon is worth one wait; a longer one is not. */
const MAX_RETRY_AFTER_SECONDS = 2;

/**
 * Shared by every visitor and keyed by path alone.
 *
 * `fetch`'s own cache keys on the request headers, and `serverFetch` sends each
 * visitor's cookies and address, so its "hourly" cache was really per visitor:
 * every crawler request was a cold miss straight into the API's rate limit. Here
 * the visitor who causes a miss still pays for it in their own rate-limit
 * allowance, but everyone after them is served from the cache. None of this data
 * depends on who is asking, so no cookie is sent.
 *
 * Failure semantics, in order:
 * - a fresh or stale cached copy is served, and a failed background refresh
 *   keeps the stale copy (`unstable_cache`), so an outage does not take down
 *   pages that have been seen before;
 * - 404 returns null — the one answer that means "does not exist";
 * - 429 with a short Retry-After is retried once;
 * - anything else transient is thrown and nothing is cached, so the page fails
 *   as a temporary error and the next request tries again.
 */
export function serverFetchPublic<T>(
  path: string,
  { revalidate }: { revalidate: number },
): Promise<T | null> {
  return fetchPublicOncePerRequest(path, revalidate) as Promise<T | null>;
}

/**
 * One request to the shared cache per render. A page and its metadata ask for
 * the same data at the same moment, and on a cold cache both missed — two API
 * calls for one page view. `fetch` deduplicated that by itself; this does it
 * for the cache. The arguments are primitives, so React's cache can key on them.
 */
const fetchPublicOncePerRequest = cache(
  async (path: string, revalidate: number): Promise<unknown> => {
    const forwarded = await visitorIdentity();
    const cached = unstable_cache(() => fetchPublic<unknown>(path, forwarded), ["public-api", path], {
      revalidate,
    });
    try {
      return await cached();
    } catch (error) {
      if (error instanceof ApiError && error.isNotFound) return null;
      throw error;
    }
  },
);

/**
 * The rate-limit identity a miss is charged to. Read outside any cache scope.
 *
 * Reading the request headers also keeps every caller rendered per request, as
 * `serverFetch` reading cookies always did: without it the sitemap became a
 * build-time page, frozen at — or failing on — whatever the API said during
 * the build.
 */
async function visitorIdentity(): Promise<Record<string, string>> {
  const { headers: incomingHeaders } = await import("next/headers");
  const incoming = await incomingHeaders();
  const secret = process.env.INTERNAL_PROXY_SECRET;
  const visitor = incoming.get("fly-client-ip");
  return secret && visitor
    ? { [PROXY_CLIENT_IP_HEADER]: visitor, [PROXY_SECRET_HEADER]: secret }
    : {};
}

export interface PublicFetchDeps {
  fetcher?: (url: string, init: RequestInit) => Promise<Response>;
  sleep?: (ms: number) => Promise<void>;
  timeoutMs?: number;
}

/** One public request, with a timeout and at most one short rate-limit retry. */
export async function fetchPublic<T>(
  path: string,
  forwarded: Record<string, string> = {},
  { fetcher = fetch, sleep = defaultSleep, timeoutMs = PUBLIC_TIMEOUT_MS }: PublicFetchDeps = {},
): Promise<T> {
  for (let attempt = 0; ; attempt += 1) {
    let response: Response;
    try {
      response = await fetcher(`${INTERNAL_ORIGIN}${API_PREFIX}${path}`, {
        headers: { Accept: "application/json", ...forwarded },
        cache: "no-store",
        signal: AbortSignal.timeout(timeoutMs),
      });
    } catch (error) {
      const timedOut = error instanceof Error && error.name === "TimeoutError";
      throw new ApiError(
        0,
        timedOut ? "UPSTREAM_TIMEOUT" : "UPSTREAM_UNREACHABLE",
        "We could not reach our data service. Please try again.",
      );
    }
    if (response.ok) return (await response.json()) as T;

    const retryAfter = Number(response.headers.get("Retry-After"));
    if (
      response.status === 429 &&
      attempt === 0 &&
      Number.isFinite(retryAfter) &&
      retryAfter > 0 &&
      retryAfter <= MAX_RETRY_AFTER_SECONDS
    ) {
      await sleep(retryAfter * 1000);
      continue;
    }
    throw await toError(response);
  }
}

function defaultSleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
