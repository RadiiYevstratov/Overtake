import type { MetadataRoute } from "next";

import { serverFetchOrNull } from "@/lib/api";
import { GUIDES } from "@/lib/guides";
import type { SeasonMeta } from "@/lib/types";

const SITE = (process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000").replace(
  /\/$/,
  "",
);

interface PlayerIndex {
  players: { slug: string; position: string; price: number; total_points: number }[];
}

/**
 * Comparison pairs, generated rather than hand-listed.
 *
 * "Salah or Haaland" is the highest-intent query shape in FPL, so these are the
 * highest-value pages in the whole SEO plan. Only same-position pairs in a
 * similar price bracket are generated: "Haaland or a £4.0m goalkeeper" is not a
 * question anybody asks, and a page answering it would be exactly the thin
 * content the quality gate exists to prevent.
 */
function comparisonPairs(
  players: PlayerIndex["players"],
  perPosition = 14,
): string[] {
  const byPosition = new Map<string, PlayerIndex["players"]>();
  for (const player of players) {
    const bucket = byPosition.get(player.position) ?? [];
    bucket.push(player);
    byPosition.set(player.position, bucket);
  }

  const pairs = new Set<string>();
  for (const bucket of byPosition.values()) {
    const top = bucket
      .sort((x, y) => y.total_points - x.total_points)
      .slice(0, perPosition);
    for (let i = 0; i < top.length; i += 1) {
      for (let j = i + 1; j < top.length; j += 1) {
        const first = top[i]!;
        const second = top[j]!;
        // Comparable price only: within £3.0m of each other.
        if (Math.abs(first.price - second.price) > 3.0) continue;
        pairs.add([first.slug, second.slug].sort().join("-vs-"));
      }
    }
  }
  return [...pairs];
}

/**
 * The sitemap covers the pages a stranger could plausibly want. League pages are
 * excluded on purpose — see `robots.ts`.
 *
 * Every generated page carries at least one number that exists nowhere else
 * (our own projection, and our measured error alongside it). A template that
 * cannot clear that bar does not ship, because a page restating public stats is
 * thin content and deserves to be treated as such.
 */
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();

  const staticPages: MetadataRoute.Sitemap = [
    { url: `${SITE}/`, lastModified: now, changeFrequency: "daily", priority: 1 },
    { url: `${SITE}/how-it-works`, lastModified: now, changeFrequency: "weekly", priority: 0.8 },
    { url: `${SITE}/pricing`, lastModified: now, changeFrequency: "monthly", priority: 0.8 },
    { url: `${SITE}/faq`, lastModified: now, changeFrequency: "monthly", priority: 0.6 },
    { url: `${SITE}/privacy`, lastModified: now, changeFrequency: "yearly", priority: 0.3 },
    { url: `${SITE}/terms`, lastModified: now, changeFrequency: "yearly", priority: 0.3 },
    { url: `${SITE}/cookies`, lastModified: now, changeFrequency: "yearly", priority: 0.3 },
  ];

  const guidePages: MetadataRoute.Sitemap = GUIDES.map((guide) => ({
    url: `${SITE}${guide.href}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.7,
  }));

  const [meta, index] = await Promise.all([
    serverFetchOrNull<SeasonMeta>("/meta/season", { revalidate: 3600 }),
    serverFetchOrNull<PlayerIndex>("/players?limit=500", { revalidate: 3600 }),
  ]);

  const playerPages: MetadataRoute.Sitemap = (index?.players ?? []).map((player) => ({
    url: `${SITE}/player/${player.slug}`,
    lastModified: now,
    changeFrequency: "weekly",
    priority: 0.6,
  }));

  // Only gameweeks that exist: linking to GW38 in August is a promise of a page
  // with nothing on it.
  const upTo = Math.min(38, (meta?.current_gameweek ?? 1) + 4);
  const gameweekPages: MetadataRoute.Sitemap = Array.from(
    { length: upTo },
    (_, index) => ({
      url: `${SITE}/gameweek/${index + 1}`,
      lastModified: now,
      changeFrequency: "weekly" as const,
      priority: index + 1 === meta?.current_gameweek ? 0.8 : 0.5,
    }),
  );

  const comparisonPages: MetadataRoute.Sitemap = comparisonPairs(
    index?.players ?? [],
  ).map((pair) => ({
    url: `${SITE}/compare/${pair}`,
    lastModified: now,
    changeFrequency: "weekly",
    priority: 0.7,
  }));

  return [
    ...staticPages,
    ...guidePages,
    ...playerPages,
    ...comparisonPages,
    ...gameweekPages,
  ];
}
