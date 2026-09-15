import { NextResponse, type NextRequest } from "next/server";

/**
 * Browser calls to the API go through the /api/v1 rewrite, so they too leave
 * from this server's address — and the API rate-limits signed-out visitors by
 * address, sign-in emails included. Vouch for the visitor's own, as serverFetch
 * does, and always strip whatever the browser sent under the same names, so a
 * visitor can never choose their own rate-limit identity.
 *
 * Header names are repeated rather than imported: middleware is bundled on its
 * own, and lib/api pulls in server-only modules.
 */
export function middleware(request: NextRequest) {
  const forwarded = new Headers(request.headers);
  forwarded.delete("x-overtake-client-ip");
  forwarded.delete("x-overtake-proxy-secret");

  const secret = process.env.INTERNAL_PROXY_SECRET;
  const visitor = request.headers.get("fly-client-ip");
  if (secret && visitor) {
    forwarded.set("x-overtake-client-ip", visitor);
    forwarded.set("x-overtake-proxy-secret", secret);
  }

  return NextResponse.next({ request: { headers: forwarded } });
}

export const config = { matcher: "/api/v1/:path*" };
