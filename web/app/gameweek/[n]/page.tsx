import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Card, RuleHeading } from "@/components/ui";
import { serverFetchOrNull } from "@/lib/api";
import { money, timestamp } from "@/lib/format";
import type { GameweekPage, ProjectedPlayer } from "@/lib/types";

type Params = Promise<{ n: string }>;

export const revalidate = 1800;

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { n } = await params;
  const data = await serverFetchOrNull<GameweekPage>(`/gameweeks/${n}`, {
    revalidate: 1800,
  });
  if (!data) return { title: "Gameweek not found" };
  return {
    title: `FPL Gameweek ${data.gameweek.id} — captain picks, differentials and projections`,
    description: `Projected points, captain options and the differentials nobody in your mini-league owns for Fantasy Premier League Gameweek ${data.gameweek.id}.`,
    alternates: { canonical: `/gameweek/${data.gameweek.id}` },
  };
}

export default async function GameweekSeoPage({ params }: { params: Params }) {
  const { n } = await params;
  const data = await serverFetchOrNull<GameweekPage>(`/gameweeks/${n}`, {
    revalidate: 1800,
  });
  if (!data) notFound();

  const { gameweek, fixtures, top_projected, differentials, captain_picks, accuracy } =
    data;
  const number = gameweek.id;

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "SportsEvent",
            name: `Fantasy Premier League Gameweek ${number}`,
            startDate: gameweek.deadline_utc,
            sport: "Association football",
          }),
        }}
      />

      <h1 className="text-4xl font-bold tracking-tight">Gameweek {number}</h1>
      <p className="mt-2 text-ink-dim">
        Deadline <span className="num">{timestamp(gameweek.deadline_utc)}</span> UTC
        {gameweek.average_score != null ? (
          <>
            {" "}
            · average score <span className="num">{gameweek.average_score}</span>
          </>
        ) : null}
      </p>

      <nav aria-label="Nearby gameweeks" className="mt-4 flex gap-3 text-sm">
        {number > 1 ? (
          <Link href={`/gameweek/${number - 1}`} className="text-ink-dim hover:text-ink">
            ← GW{number - 1}
          </Link>
        ) : null}
        {number < 38 ? (
          <Link href={`/gameweek/${number + 1}`} className="text-ink-dim hover:text-ink">
            GW{number + 1} →
          </Link>
        ) : null}
      </nav>

      <section className="mt-10">
        <RuleHeading>Captain picks</RuleHeading>
        <PlayerTable rows={captain_picks} emptyLabel="No projections for this gameweek yet." />
      </section>

      {/* On-thesis: differentials are the mini-league lever. */}
      <section className="mt-10">
        <RuleHeading>Differentials — under 10% owned</RuleHeading>
        <p className="mb-4 leading-relaxed text-ink-dim">
          A player everyone owns cannot gain you anything on the people in your league.
          These are the highest-projected players almost nobody has.
        </p>
        <PlayerTable
          rows={differentials}
          emptyLabel="Nothing under 10% ownership projects well this gameweek."
        />
      </section>

      <section className="mt-10">
        <RuleHeading>Highest projected overall</RuleHeading>
        <PlayerTable rows={top_projected} emptyLabel="No projections yet." />
      </section>

      {fixtures.length > 0 ? (
        <section className="mt-10">
          <RuleHeading>Fixtures</RuleHeading>
          <div className="scroll-x">
            <table className="w-full border-collapse text-sm">
              <caption className="sr-only">Gameweek {number} fixtures</caption>
              <thead>
                <tr className="border-b border-border text-left text-[11px] uppercase tracking-wider text-ink-faint">
                  <th scope="col" className="py-2 pr-4 font-semibold">Home</th>
                  <th scope="col" className="py-2 pr-4 font-semibold">Away</th>
                  <th scope="col" className="py-2 pr-4 text-right font-semibold">FDR</th>
                  <th scope="col" className="py-2 text-right font-semibold">Result</th>
                </tr>
              </thead>
              <tbody>
                {fixtures.map((fixture, index) => (
                  <tr key={index} className="border-b border-border/60">
                    <td className="py-2 pr-4">{fixture.home}</td>
                    <td className="py-2 pr-4">{fixture.away}</td>
                    <td className="num py-2 pr-4 text-right text-ink-dim">
                      {fixture.home_difficulty}–{fixture.away_difficulty}
                    </td>
                    <td className="num py-2 text-right">
                      {fixture.score ?? (
                        <span className="text-ink-faint">
                          {timestamp(fixture.kickoff_utc)}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <p className="mt-8 text-xs text-ink-faint">
        Projections are ours, not FPL&apos;s.{" "}
        {accuracy.mae != null ? (
          <>
            Measured error <span className="num">{accuracy.mae.toFixed(2)}</span> points
            per player per gameweek.{" "}
          </>
        ) : null}
        <Link href="/how-it-works" className="underline hover:text-ink-dim">
          How we calculate them
        </Link>
      </p>

      <Card className="mt-10 p-6">
        <h2 className="text-lg font-semibold">
          Which of these actually helps you in your league?
        </h2>
        <p className="mt-2 leading-relaxed text-ink-dim">
          That depends entirely on who your rivals already own. Paste your league ID and
          Overtake works out which of these moves closes the gap on the specific people
          you are racing.
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

function PlayerTable({
  rows,
  emptyLabel,
}: {
  rows: ProjectedPlayer[];
  emptyLabel: string;
}) {
  if (rows.length === 0) {
    return <p className="text-sm text-ink-dim">{emptyLabel}</p>;
  }
  return (
    <div className="scroll-x">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-border text-left text-[11px] uppercase tracking-wider text-ink-faint">
            <th scope="col" className="py-2 pr-4 font-semibold">Player</th>
            <th scope="col" className="py-2 pr-4 font-semibold">Team</th>
            <th scope="col" className="py-2 pr-4 font-semibold">Pos</th>
            <th scope="col" className="py-2 pr-4 text-right font-semibold">Price</th>
            <th scope="col" className="py-2 pr-4 text-right font-semibold">Owned</th>
            <th scope="col" className="py-2 text-right font-semibold">Projected</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.slug} className="border-b border-border/60">
              <th scope="row" className="py-2 pr-4 text-left font-medium">
                <Link href={`/player/${row.slug}`} className="hover:text-you">
                  {row.name}
                </Link>
              </th>
              <td className="py-2 pr-4 text-ink-dim">{row.team_short}</td>
              <td className="py-2 pr-4 text-ink-dim">{row.position}</td>
              <td className="num py-2 pr-4 text-right">{money(row.price)}</td>
              <td className="num py-2 pr-4 text-right text-ink-dim">
                {row.selected_by_percent.toFixed(1)}%
              </td>
              <td className="num py-2 text-right font-medium text-you">
                {row.projected_points.toFixed(1)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
