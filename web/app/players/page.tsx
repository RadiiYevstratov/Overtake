import type { Metadata } from "next";
import Link from "next/link";

import { RuleHeading } from "@/components/ui";
import { money } from "@/lib/format";
import { serverFetchPublic } from "@/lib/public-api";
import { absoluteUrl } from "@/lib/site";

export const revalidate = 3600;

export const metadata: Metadata = {
  title: "FPL players — prices, points and our projections",
  description:
    "Every Fantasy Premier League player we project, by position, with price, points and ownership. Each links to our own six-gameweek projection and measured error.",
  alternates: { canonical: "/players" },
};

interface PlayerIndex {
  players: {
    slug: string;
    name: string;
    team_short: string | null;
    position: string;
    price: number;
    total_points: number;
    selected_by_percent: number;
  }[];
}

const POSITIONS: { code: string; label: string }[] = [
  { code: "GKP", label: "Goalkeepers" },
  { code: "DEF", label: "Defenders" },
  { code: "MID", label: "Midfielders" },
  { code: "FWD", label: "Forwards" },
];

/**
 * The index every player page's breadcrumb points to, and the crawl path into
 * them: one link to each page in the sitemap's player set, grouped as FPL
 * groups them. A failing API is a temporary error here, never an empty list.
 */
export default async function PlayersPage() {
  const index = await serverFetchPublic<PlayerIndex>("/players?limit=500", {
    revalidate: 3600,
  });
  const players = index?.players ?? [];

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            itemListElement: [
              { "@type": "ListItem", position: 1, name: "Overtake", item: absoluteUrl("/") },
              { "@type": "ListItem", position: 2, name: "Players", item: absoluteUrl("/players") },
            ],
          }),
        }}
      />

      <nav aria-label="Breadcrumb" className="text-sm text-ink-faint">
        <Link href="/" className="hover:text-ink">
          Overtake
        </Link>
      </nav>
      <h1 className="mt-3 text-4xl font-bold tracking-tight">FPL players</h1>
      <p className="mt-2 text-ink-dim">
        The {players.length} highest-scoring players this season, by position. Each page
        has our own projection for the next six gameweeks, published with its measured
        error.
      </p>

      {POSITIONS.map(({ code, label }) => {
        const rows = players.filter((player) => player.position === code);
        if (rows.length === 0) return null;
        return (
          <section key={code} className="mt-10">
            <RuleHeading>{label}</RuleHeading>
            <div className="scroll-x">
              <table className="w-full border-collapse text-sm">
                <caption className="sr-only">{label}</caption>
                <thead>
                  <tr className="border-b border-border text-left text-[11px] uppercase tracking-wider text-ink-faint">
                    <th scope="col" className="py-2 pr-4 font-semibold">Player</th>
                    <th scope="col" className="py-2 pr-4 font-semibold">Team</th>
                    <th scope="col" className="py-2 pr-4 text-right font-semibold">Price</th>
                    <th scope="col" className="py-2 pr-4 text-right font-semibold">Owned</th>
                    <th scope="col" className="py-2 text-right font-semibold">Points</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((player) => (
                    <tr key={player.slug} className="border-b border-border/60">
                      <th scope="row" className="py-2 pr-4 text-left font-medium">
                        <Link href={`/player/${player.slug}`} className="hover:text-you">
                          {player.name}
                        </Link>
                      </th>
                      <td className="py-2 pr-4 text-ink-dim">{player.team_short ?? "—"}</td>
                      <td className="num py-2 pr-4 text-right">{money(player.price)}</td>
                      <td className="num py-2 pr-4 text-right text-ink-dim">
                        {player.selected_by_percent.toFixed(1)}%
                      </td>
                      <td className="num py-2 text-right">{player.total_points}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        );
      })}
    </div>
  );
}
