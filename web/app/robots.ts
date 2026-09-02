import type { MetadataRoute } from "next";

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

/**
 * League pages are deliberately excluded: they contain other people's team
 * names and are of no value to a stranger. They remain fully shareable by URL —
 * shareability and indexability are different goals.
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
        disallow: ["/l/", "/app/", "/signin", "/unsubscribe", "/api/"],
      },
    ],
    sitemap: `${SITE}/sitemap.xml`,
    host: SITE,
  };
}
