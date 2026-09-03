import type { Metadata } from "next";
import Link from "next/link";
import { notFound, permanentRedirect } from "next/navigation";

import { Badge, Card, RuleHeading, cx } from "@/components/ui";
import { serverFetchOrNull } from "@/lib/api";
import { money, signedPoints } from "@/lib/format";
import type { PlayerComparison } from "@/lib/types";

type Params = Promise<{ pair: string }>;

export const revalidate = 3600;

/**
 * "Salah or Haaland" is the highest-intent query shape in FPL, and the honest
 * answer is not "whoever scores more" — it is "whichever one the people in your
 * league do not already own". That is the angle no incumbent can write from,
 * and it is what this page leads with.
 *
 * One canonical order per pair: `a-vs-b` is canonical when a sorts first, and
 * `b-vs-a` permanently redirects to it. Two URLs for one comparison would split
 * the ranking signal between them.
 */
function parsePair(pair: string): { a: string; b: string } | null {
  const parts = pair.split("-vs-");
  if (parts.length !== 2) return null;
  const [a, b] = parts;
  if (!a || !b || a === b) return null;
  return { a, b };
}

function canonicalPair(a: string, b: string): string {
  return [a, b].sort()[0] === a ? `${a}-vs-${b}` : `${b}-vs-${a}`;
}

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { pair } = await params;
  const parsed = parsePair(pair);
  if (!parsed) return { title: "Not found" };

  const data = await serverFetchOrNull<PlayerComparison>(
    `/players/${parsed.a}/vs/${parsed.b}`,
    { revalidate: 3600 },
  );
  if (!data) return { title: "Not found" };

  const canonical = canonicalPair(parsed.a, parsed.b);
  return {
    title: `${data.a.name} or ${data.b.name}? FPL comparison`,
    description: `${data.a.name} (${money(data.a.price)}) projects ${data.a.expected_points_next_6} points over six gameweeks against ${data.b.name}'s ${data.b.expected_points_next_6} — and one of them is far less owned in your mini-league.`,
    alternates: { canonical: `/compare/${canonical}` },
  };
}

export default async function ComparePage({ params }: { params: Params }) {
  const { pair } = await params;
  const parsed = parsePair(pair);
  if (!parsed) notFound();

  // Resolve before redirecting. Redirecting first would send a crawler to a
  // canonical URL that then 404s, which wastes a round trip and looks like a
  // broken site rather than a missing player.
  const data = await serverFetchOrNull<PlayerComparison>(
    `/players/${parsed.a}/vs/${parsed.b}`,
    { revalidate: 3600 },
  );
  if (!data) notFound();

  const canonical = canonicalPair(parsed.a, parsed.b);
  if (canonical !== pair) permanentRedirect(`/compare/${canonical}`);

  const { a, b, points_delta, verdict, differential_pick, accuracy } = data;
  const winner = verdict === "a" ? a : verdict === "b" ? b : null;
  const differential = differential_pick === a.slug ? a : b;

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "Article",
            headline: `${a.name} or ${b.name}? FPL comparison`,
            author: { "@type": "Organization", name: "Overtake" },
          }),
        }}
      />

      <h1 className="text-4xl font-bold tracking-tight">
        {a.name} <span className="text-ink-faint">or</span> {b.name}?
      </h1>
      <p className="mt-3 text-lg leading-relaxed text-ink-dim">
        {winner ? (
          <>
            On projected points alone, <span className="text-ink">{winner.name}</span> is
            ahead by{" "}
            <span className="num text-ink">{Math.abs(points_delta).toFixed(1)}</span>{" "}
            over the next six gameweeks. That is not the whole answer.
          </>
        ) : (
          <>
            On projected points they are within{" "}
            <span className="num text-ink">{Math.abs(points_delta).toFixed(1)}</span> of
            each other over six gameweeks — close enough that points are not the thing
            that should decide it.
          </>
        )}
      </p>

      {!data.same_position ? (
        <p className="mt-3">
          <Badge tone="warn">
            Different positions — {a.position} versus {b.position}
          </Badge>
        </p>
      ) : null}

      {/* ------------------------------------------------ side by side */}
      <div className="mt-8 grid gap-4 sm:grid-cols-2">
        <PlayerColumn player={a} highlight={verdict === "a"} />
        <PlayerColumn player={b} highlight={verdict === "b"} />
      </div>

      {/* -------------------------------------------- the real answer */}
      <section className="mt-10">
        <RuleHeading>The answer nobody else gives you</RuleHeading>
        <Card className="border-you-dim p-6">
          <p className="text-lg leading-relaxed">
            <span className="text-you">{differential.name}</span> is owned by{" "}
            <span className="num">{differential.selected_by_percent.toFixed(1)}%</span> of
            managers, against{" "}
            <span className="num">
              {(differential.slug === a.slug ? b : a).selected_by_percent.toFixed(1)}%
            </span>{" "}
            for {(differential.slug === a.slug ? b : a).name}.
          </p>
          <p className="mt-3 leading-relaxed text-ink-dim">
            If you are chasing someone in your mini-league, the less-owned player is
            usually the right pick even when he projects slightly lower — points from a
            player your rival also owns cancel out and cannot close the gap. If you are
            defending a lead, take the one your rival already has: matching them removes
            their chance to gain on you.
          </p>
          <p className="mt-4 text-sm text-ink-faint">
            Global ownership is only a proxy. What actually matters is whether the
            specific people in <em>your</em> league own him.
          </p>
          <Link
            href="/"
            className="mt-5 inline-flex min-h-[44px] items-center rounded-[8px] bg-you px-5 py-2.5 text-sm font-semibold text-[#06231a] transition-colors hover:bg-[#4ae8a5]"
          >
            Check who owns them in my league
          </Link>
        </Card>
      </section>

      {/* ------------------------------------------------ per gameweek */}
      {a.per_gameweek.length > 0 ? (
        <section className="mt-10">
          <RuleHeading>Projected by gameweek</RuleHeading>
          <div className="scroll-x">
            <table className="w-full border-collapse text-sm">
              <caption className="sr-only">
                Projected points for {a.name} and {b.name} by gameweek
              </caption>
              <thead>
                <tr className="border-b border-border text-left text-[11px] uppercase tracking-wider text-ink-faint">
                  <th scope="col" className="py-2 pr-4 font-semibold">
                    GW
                  </th>
                  <th scope="col" className="py-2 pr-4 text-right font-semibold">
                    {a.name}
                  </th>
                  <th scope="col" className="py-2 pr-4 text-right font-semibold">
                    {b.name}
                  </th>
                  <th scope="col" className="py-2 text-right font-semibold">
                    Difference
                  </th>
                </tr>
              </thead>
              <tbody>
                {data.horizon.map((gameweek) => {
                  const rowA = a.per_gameweek.find((r) => r.gameweek === gameweek);
                  const rowB = b.per_gameweek.find((r) => r.gameweek === gameweek);
                  const diff = (rowA?.mu ?? 0) - (rowB?.mu ?? 0);
                  return (
                    <tr key={gameweek} className="border-b border-border/60">
                      <td className="num py-2 pr-4">{gameweek}</td>
                      <td className="num py-2 pr-4 text-right">
                        {rowA ? rowA.mu.toFixed(1) : "—"}
                      </td>
                      <td className="num py-2 pr-4 text-right">
                        {rowB ? rowB.mu.toFixed(1) : "—"}
                      </td>
                      <td
                        className={cx(
                          "num py-2 text-right",
                          Math.abs(diff) < 0.1
                            ? "text-ink-faint"
                            : diff > 0
                              ? "text-you"
                              : "text-rival",
                        )}
                      >
                        {Math.abs(diff) < 0.1 ? "level" : signedPoints(diff)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      <p className="mt-8 text-xs leading-relaxed text-ink-faint">
        Projections are ours, not FPL&apos;s.{" "}
        {accuracy.mae != null ? (
          <>
            Measured error <span className="num">{accuracy.mae.toFixed(2)}</span> points
            per player per gameweek over the last{" "}
            <span className="num">{accuracy.gameweeks}</span>.{" "}
          </>
        ) : null}
        <Link href="/how-it-works" className="underline hover:text-ink-dim">
          How we calculate them
        </Link>
      </p>

      <nav aria-label="Player pages" className="mt-8 flex flex-wrap gap-4 text-sm">
        <Link href={`/player/${a.slug}`} className="text-ink-dim hover:text-ink">
          {a.name}&apos;s full page →
        </Link>
        <Link href={`/player/${b.slug}`} className="text-ink-dim hover:text-ink">
          {b.name}&apos;s full page →
        </Link>
      </nav>
    </div>
  );
}

function PlayerColumn({
  player,
  highlight,
}: {
  player: PlayerComparison["a"];
  highlight: boolean;
}) {
  return (
    <Card className={cx("p-5", highlight && "border-you-dim")}>
      <h2 className="text-xl font-semibold">
        <Link href={`/player/${player.slug}`} className="hover:text-you">
          {player.name}
        </Link>
      </h2>
      <p className="mt-1 text-sm text-ink-dim">
        {player.team} · {player.position} · {money(player.price)}
      </p>
      {player.news ? (
        <p className="mt-2 text-xs text-warn">{player.news}</p>
      ) : null}

      <dl className="mt-4 space-y-2 text-sm">
        <Row
          label="Projected, next 6 GW"
          value={player.expected_points_next_6.toFixed(1)}
          strong
        />
        <Row
          label="Chance of starting"
          value={
            player.start_probability === null
              ? "—"
              : `${Math.round(player.start_probability * 100)}%`
          }
        />
        <Row label="Owned by" value={`${player.selected_by_percent.toFixed(1)}%`} />
        <Row label="Points this season" value={String(player.total_points)} />
        <Row label="Minutes" value={String(player.minutes)} />
      </dl>

      {player.is_set_piece_taker ? (
        <p className="mt-4">
          <Badge tone="you">Set-piece taker</Badge>
        </p>
      ) : null}
    </Card>
  );
}

function Row({
  label,
  value,
  strong,
}: {
  label: string;
  value: string;
  strong?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-ink-faint">{label}</dt>
      <dd className={cx("num", strong ? "text-lg font-semibold text-you" : "text-ink")}>
        {value}
      </dd>
    </div>
  );
}
