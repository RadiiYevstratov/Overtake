/**
 * Liveness for the web server itself.
 *
 * Deliberately dumb: no API call, no database, no rendering. It answers the
 * only question a platform health check should ask — "is this process serving
 * HTTP?" — so a slow upstream or a signed-out redirect can never be mistaken
 * for a dead machine.
 *
 * The landing page is the wrong probe for this. It renders, fetches upstream,
 * and is entitled to redirect, so any of those turns a healthy machine into a
 * failed deploy. Whether the app is *useful* is what the E2E journeys check.
 */
export const dynamic = "force-dynamic";

export function GET(): Response {
  return new Response("ok", {
    status: 200,
    headers: {
      "content-type": "text/plain; charset=utf-8",
      "cache-control": "no-store",
    },
  });
}
