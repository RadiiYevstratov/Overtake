import { cookies } from "next/headers";

/** The API's session cookie. Matches SESSION_COOKIE_NAME in core/security.py. */
const SESSION_COOKIE = "overtake_session";

/**
 * Whether this request carries a session at all.
 *
 * Public pages ask the API who the visitor is so the header can greet them. For
 * a visitor with no session cookie there is nothing to ask about, and the answer
 * is a round-trip that writes a rate-limit row — which wakes a database that
 * scales to zero and bills by the hour. Search-engine crawlers walk the public
 * pages all day and are signed out by definition, so that was most of it.
 *
 * Cheap and honest: no cookie, no session, and the page renders signed out
 * exactly as it would have.
 */
export async function hasSession(): Promise<boolean> {
  return (await cookies()).has(SESSION_COOKIE);
}
