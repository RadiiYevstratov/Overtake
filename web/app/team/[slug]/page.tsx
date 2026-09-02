import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Card, RuleHeading, cx } from "@/components/ui";
import { serverFetchOrNull } from "@/lib/api";
import { money } from "@/lib/format";

type Params = Promise<{ slug: string }>;

export const revalidate = 3600;

interface TeamPage {
  team: { id: number; slug: string; name: string; short_name: string };
  players: {
    slug: string;
    name: string;
    position: string;
    price: number;
    total_points: number;
    selected_by_percent: number;
  }[];
  fixtures: {
    gameweek: number | null;
    opponent: string | null;
    is_home: boolean;
    difficulty: number | null;
  }[];
}

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { slug } = await params;
  const data = await serverFetchOrNull<TeamPage>(`/teams/${slug}`, { revalidate: 3600 });
  if (!data) return { title: "Club not found" };
  return {
    title: `${data.team.name} FPL players, prices and fixtures`,
    description: `Every ${data.team.name} player in Fantasy Premier League with prices, ownership and our own projections, plus the upcoming fixture run.`,
    alternates: { canonical: `/team/${data.team.slug}` },
  };
}

export default async function TeamSeoPage({ params }: { params: Params }) {
  const { slug } = await params;
  const data = await serverFetchOrNull<TeamPage>(`/teams/${slug}`, { revalidate: 3600 });
  if (!data) notFound();

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <h1 className="text-4xl font-bold tracking-tight">{data.team.name}</h1>
      <p className="mt-2 text-ink-dim">
        Fantasy Premier League squad, prices and fixtures
      </p>

      {data.fixtures.length > 0 ? (
        <section className="mt-8">
          <RuleHeading>Next fixtures</RuleHeading>
          <ul className="flex flex-wrap gap-2">
            {data.fixtures.map((fixture, index) => (
              <li key={index}>
                <span
                  className={cx(
                    "inline-flex items-center gap-1.5 rounded-[8px] border px-3 py-1.5 text-sm",
                    (fixture.difficulty ?? 3) <= 2
                      ? "border-you-dim text-you"
                      : (fixture.difficulty ?? 3) >= 4
                        ? "border-rival-dim text-rival"
                        : "border-border text-ink-dim",
                  )}
                >
                  <span className="num text-[11px] text-ink-faint">
                    GW{fixture.gameweek}
                  </span>
                  {fixture.opponent} ({fixture.is_home ? "H" : "A"})
                  <span className="num text-[11px]">{fixture.difficulty}</span>
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-ink-faint">
            Difficulty is the official FPL Fixture Difficulty Rating, 1 easiest to 5
            hardest.
          </p>
        </section>
      ) : null}

      <section className="mt-10">
        <RuleHeading>Squad</RuleHeading>
        <div className="scroll-x">
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">{data.team.name} FPL squad</caption>
            <thead>
              <tr className="border-b border-border text-left text-[11px] uppercase tracking-wider text-ink-faint">
                <th scope="col" className="py-2 pr-4 font-semibold">
                  Player
                </th>
                <th scope="col" className="py-2 pr-4 font-semibold">
                  Pos
                </th>
                <th scope="col" className="py-2 pr-4 text-right font-semibold">
                  Price
                </th>
                <th scope="col" className="py-2 pr-4 text-right font-semibold">
                  Owned
                </th>
                <th scope="col" className="py-2 text-right font-semibold">
                  Points
                </th>
              </tr>
            </thead>
            <tbody>
              {data.players.map((player) => (
                <tr key={player.slug} className="border-b border-border/60">
                  <th scope="row" className="py-2 pr-4 text-left font-medium">
                    <Link href={`/player/${player.slug}`} className="hover:text-you">
                      {player.name}
                    </Link>
                  </th>
                  <td className="py-2 pr-4 text-ink-dim">{player.position}</td>
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

      <Card className="mt-10 p-6">
        <h2 className="text-lg font-semibold">
          Which of these do your rivals already own?
        </h2>
        <p className="mt-2 leading-relaxed text-ink-dim">
          That is the number that decides whether any of them can help you. Paste your
          league ID and find out.
        </p>
        <Link
          href="/"
          className="mt-4 inline-flex min-h-[44px] items-center rounded-[8px] bg-you px-5 py-2.5 text-sm font-semibold text-[#06231a] transition-colors hover:bg-[#4ae8a5]"
        >
          Check my league
        </Link>
      </Card>
    </div>
  );
}
