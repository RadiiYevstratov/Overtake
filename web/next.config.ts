import type { NextConfig } from "next";

/**
 * The API is proxied under the same origin so the session cookie is a
 * first-party cookie. That removes the whole class of third-party-cookie and
 * CORS problems, and means the double-submit CSRF token works without any
 * cross-site exemption.
 */
const API_ORIGIN = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // Emits .next/standalone: the server plus only the node_modules it actually
  // reaches. It is what keeps the container image small enough to deploy
  // quickly, and `next start` still works locally and in the E2E run.
  output: "standalone",

  // Without this, Next walks up, finds the package.json at the repository root
  // and treats that as the workspace root — so the output lands at
  // .next/standalone/web/server.js instead of .next/standalone/server.js and
  // the container starts nothing. Pinning the root keeps the layout stable no
  // matter what appears above this directory.
  outputFileTracingRoot: __dirname,
  reactStrictMode: true,
  poweredByHeader: false,
  compress: true,
  productionBrowserSourceMaps: false,

  // One canonical host. www and the platform hostname answer with a permanent
  // redirect, so search engines consolidate every page on the real domain
  // instead of splitting the ranking signal across three copies of the site.
  // Redirects run before rewrites, so an old sign-in link pointing at the
  // platform hostname still reaches the API — via the canonical domain.
  async redirects() {
    const canonical = process.env.NEXT_PUBLIC_SITE_URL;
    if (!canonical) return [];
    const canonicalHost = new URL(canonical).host;
    const aliases = [`www.${canonicalHost}`, "overtake-web.fly.dev"].filter(
      (host) => host !== canonicalHost,
    );
    return aliases.map((host) => ({
      source: "/:path*",
      has: [{ type: "host" as const, value: host.replace(/\./g, "\\.") }],
      destination: `${canonical}/:path*`,
      permanent: true,
    }));
  },

  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${API_ORIGIN}/api/v1/:path*` }];
  },

  async headers() {
    // Next's dev server compiles with eval-based source maps and hot reloading,
    // which a production-strength script-src blocks outright. The relaxation is
    // scoped to development so production keeps the strict policy.
    const isDev = process.env.NODE_ENV !== "production";
    const scriptSrc = isDev
      ? "script-src 'self' 'unsafe-inline' 'unsafe-eval'"
      : "script-src 'self' 'unsafe-inline'";

    const csp = [
      "default-src 'self'",
      // Next injects inline bootstrap scripts; 'unsafe-inline' is required for
      // them and is why nothing else on the page is allowed to load scripts.
      scriptSrc,
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob:",
      "font-src 'self' data:",
      // The dev server's hot-reload channel is a websocket back to itself.
      isDev ? "connect-src 'self' ws: wss:" : "connect-src 'self'",
      "frame-ancestors 'none'",
      "form-action 'self'",
      "base-uri 'self'",
      "object-src 'none'",
      ...(isDev ? [] : ["upgrade-insecure-requests"]),
    ].join("; ");

    return [
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: csp },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "DENY" },
          // HSTS: once a browser has seen this, it refuses plain HTTP for the
          // whole domain — so a link someone taps in a group chat as http:// is
          // never sent in the clear before the redirect. Matches the API's
          // policy. Deliberately no `preload`: that is effectively irreversible
          // and a decision for the domain owner, not a default.
          ...(isDev
            ? []
            : [
                {
                  key: "Strict-Transport-Security",
                  value: "max-age=31536000; includeSubDomains",
                },
              ]),
          {
            key: "Permissions-Policy",
            value: "geolocation=(), microphone=(), camera=(), payment=(), interest-cohort=()",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
