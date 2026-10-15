/** The canonical origin, for the places that need absolute URLs (sitemap, JSON-LD). */
export const SITE = (process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000").replace(
  /\/$/,
  "",
);

export function absoluteUrl(path: string): string {
  return `${SITE}${path.startsWith("/") ? path : `/${path}`}`;
}

/**
 * The default share card. Pages without their own image inherit it from the
 * root layout; a page that sets its own `openGraph` must pass it on, because
 * Next replaces the whole `openGraph` object rather than merging it.
 */
export const DEFAULT_OG_IMAGE = {
  url: "/og.png",
  width: 1200,
  height: 630,
  alt: "Overtake — beat the people in your FPL mini-league",
};
