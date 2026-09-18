/**
 * Server-side error reporting for the web app.
 *
 * A page can fail on this server without the API ever erring — the signed-in
 * pages that crashed reading `me.plan` of null were exactly that, and nothing
 * told anyone. Next calls `onRequestError` for every server error; this posts
 * it to the API, which sends the operator the same deduplicated alert it sends
 * for its own failures.
 *
 * Authenticated by the proxy secret the two apps already share, so it needs no
 * new configuration. It never throws and never delays the failing request by
 * more than the short timeout below.
 */

type RequestInfo = { path: string; method: string };
type ErrorContext = { routeType?: string; routePath?: string };

// Navigation control flow, not failures: `redirect()` and `notFound()` throw
// errors carrying these digests on purpose.
const NOT_ERRORS = ["NEXT_REDIRECT", "NEXT_HTTP_ERROR_FALLBACK", "NEXT_NOT_FOUND"];

export async function onRequestError(
  error: unknown,
  request: RequestInfo,
  context: ErrorContext,
): Promise<void> {
  const secret = process.env.INTERNAL_PROXY_SECRET;
  if (!secret) return;

  const digest =
    typeof error === "object" && error !== null && "digest" in error
      ? String((error as { digest: unknown }).digest ?? "")
      : "";
  if (NOT_ERRORS.some((marker) => digest.startsWith(marker))) return;

  const message = error instanceof Error ? `${error.name}: ${error.message}` : String(error);
  const origin = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";

  try {
    await fetch(`${origin}/api/v1/ops/report`, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "X-Overtake-Proxy-Secret": secret,
      },
      body: JSON.stringify({
        // Path only: the API drops the query string too, but it need never leave here.
        path: (context.routePath ?? request.path).split("?")[0]?.slice(0, 300),
        kind: context.routeType ?? "render",
        message: message.slice(0, 500),
        digest: digest.slice(0, 80) || null,
      }),
      signal: AbortSignal.timeout(3000),
    });
  } catch {
    // Reporting an error must never become a second one.
  }
}
