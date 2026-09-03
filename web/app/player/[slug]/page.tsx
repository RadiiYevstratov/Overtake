import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Badge, Card, RuleHeading } from "@/components/ui";
import { serverFetchOrNull } from "@/lib/api";
import { money } from "@/lib/format";
import type { PlayerPage } from "@/lib/types";

type Params = Promise<{ slug: string }>;

interface ComparablePlayer {
  slug: string;
  name: string;
  price: number;
}

const POSITION_CODES: Record<string, number> = {
  GKP: 1,
  DEF: 2,
  MID: 3,
  FWD: 4,
};

// Player pages revalidate hourly: prices and availability move daily, and a
// stale projection is worse than a slightly slower page.
export const revalidate = 3600;

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  const { slug } = await params;
  const data = await serverFetchOrNull<PlayerPage>(`/players/${slug}`, {
    revalidate: 3600,
  });
  if (!data) return { title: "Player not found" };
  const { player, projection } = data;
  return {
    title: `${player.name} FPL — ${projection.expected_points_next_6} points projected over 6 gameweeks`,
    description: `${player.name} (${player.team}, ${player.position}, ${money(player.price)}) is projected ${projection.expected_points_next_6} points over the next six gameweeks, owned by ${player.selected_by_percent}% of managers.`,
    alternates: { canonical: `/player/${player.slug}` },
  };
}

export default async function PlayerSeoPage({ params }: { params: Params }) {
  const { slug } = await params;
  const data = await serverFetchOrNull<PlayerPage>(`/players/${slug}`, {
    revalidate: 3600,
  });
  if (!data) notFound();

  const { player, projection, history, fixtures, accuracy } = data;
  const totalPoints = history.reduce((sum, row) => sum + row.points, 0);

  // Internal linking is the link-equity engine: every player page points at its
  // comparison pages, its club page and the current gameweek.
  const rivals = await serverFetchOrNull<{ players: ComparablePlayer[] }>(
    `/players?position=${POSITION_CODES[player.position] ?? 3}&limit=40`,
    { revalidate: 3600 },
  );
  const comparisons = (rivals?.players ?? [])
    .filter(
      (other) =>
        other.slug !== player.slug && Math.abs(other.price - player.price) <= 3.0,
    )
    .slice(0, 6);

  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            itemListElement: [
              { "@type": "ListItem", position: 1, name: "Players", item: "/players" },
              {
                "@type": "ListItem",
                position: 2,
                name: player.name,
                item: `/player/${player.slug}`,
              },
            ],
          }),
        }}
      />

      <nav aria-label="Breadcrumb" className="text-sm text-ink-faint">
        <Link href="/" className="hover:text-ink">
          Overtake
        </Link>
        {player.team_slug ? (
          <>
            {" / "}
            <Link href={`/team/${player.team_slug}`} className="hover:text-ink">
              {player.team}
            </Link>
          </>
        ) : null}
      </nav>

      <header className="mt-3">
        <h1 className="text-4xl font-bold tracking-tight">{player.name}</h1>
        <p className="mt-2 text-ink-dim">
          {player.full_name || player.name} · {player.team} · {player.position} ·{" "}
          <span className="num">{money(player.price)}</span>
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {player.is_set_piece_taker ? <Badge tone="you">Set-piece taker</Badge> : null}
          {player.status !== "a" ? <Badge tone="warn">Availability doubt</Badge> : null}
          <Badge>
            <span className="num">{player.selected_by_percent}%</span>&nbsp;owned
          </Badge>
        </div>
        {player.news ? (
          <p className="mt-3 rounded-[8px] border border-[#5a4a15] bg-[#1e1a0c] px-4 py-3 text-sm text-warn">
            {player.news}
          </p>
        ) : null}
      </header>

      {/* The quality gate: a number that exists nowhere else. */}
      <Card className="mt-8 p-6">
        <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
          <Figure
            value={projection.expected_points_next_6.toFixed(1)}
            label="projected, next 6 GW"
            tone="you"
          />
          <Figure
            value={
              projection.start_probability === null
                ? "—"
                : `${Math.round(projection.start_probability * 100)}%`
            }
            label="chance of starting"
          />
          <Figure value={String(player.total_points)} label="points this season" />
          <Figure value={String(player.minutes)} label="minutes played" />
        </div>
        <p className="mt-5 text-xs text-ink-faint">
          Our own projection, not FPL&apos;s.{" "}
          {accuracy.mae != null ? (
            <>
              Measured error{" "}
              <span className="num">{accuracy.mae.toFixed(2)}</span> points per player
              per gameweek over the last{" "}
              <span className="num">{accuracy.gameweeks}</span>.
            </>
          ) : (
            "Error not yet measurable this season."
          )}{" "}
          <Link href="/how-it-works" className="underline hover:text-ink-dim">
            How we calculate it
          </Link>
        </p>
      </Card>

      {projection.per_gameweek.length > 0 ? (
        <section className="mt-10">
          <RuleHeading>Projected by gameweek</RuleHeading>
          <div className="scroll-x">
            <table className="w-full border-collapse text-sm">
              <caption className="sr-only">
                Projected points for {player.name} by gameweek
              </caption>
              <thead>
                <tr className="border-b border-border text-left text-[11px] uppercase tracking-wider text-ink-faint">
                  <th scope="col" className="py-2 pr-4 font-semibold">
                    GW
                  </th>
                  <th scope="col" className="py-2 pr-4 font-semibold">
                    Opponent
                  </th>
                  <th scope="col" className="py-2 pr-4 text-right font-semibold">
                    Difficulty
                  </th>
                  <th scope="col" className="py-2 text-right font-semibold">
                    Projected
                  </th>
                </tr>
              </thead>
              <tbody>
                {projection.per_gameweek.map((row) => {
                  const fixture = fixtures.find((f) => f.gameweek === row.gameweek);
                  return (
                    <tr key={row.gameweek} className="border-b border-border/60">
                      <td className="num py-2 pr-4">{row.gameweek}</td>
                      <td className="py-2 pr-4">
                        {fixture ? (
                          <>
                            {fixture.opponent}{" "}
                            <span className="text-ink-faint">
                              ({fixture.is_home ? "H" : "A"})
                            </span>
                          </>
                        ) : (
                          <span className="text-ink-faint">blank</span>
                        )}
                      </td>
                      <td className="num py-2 pr-4 text-right text-ink-dim">
                        {fixture?.difficulty ?? "—"}
                      </td>
                      <td className="num py-2 text-right">{row.mu.toFixed(1)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {history.length > 0 ? (
        <section className="mt-10">
          <RuleHeading>What actually happened</RuleHeading>
          <div className="scroll-x">
            <table className="w-full border-collapse text-sm">
              <caption className="sr-only">
                {player.name} results by completed gameweek
              </caption>
              <thead>
                <tr className="border-b border-border text-left text-[11px] uppercase tracking-wider text-ink-faint">
                  <th scope="col" className="py-2 pr-4 font-semibold">GW</th>
                  <th scope="col" className="py-2 pr-4 text-right font-semibold">Pts</th>
                  <th scope="col" className="py-2 pr-4 text-right font-semibold">Mins</th>
                  <th scope="col" className="py-2 pr-4 text-right font-semibold">G</th>
                  <th scope="col" className="py-2 pr-4 text-right font-semibold">A</th>
                  <th scope="col" className="py-2 text-right font-semibold">Bonus</th>
                </tr>
              </thead>
              <tbody>
                {history.map((row) => (
                  <tr key={row.gameweek} className="border-b border-border/60">
                    <td className="num py-2 pr-4">{row.gameweek}</td>
                    <td className="num py-2 pr-4 text-right font-medium">{row.points}</td>
                    <td className="num py-2 pr-4 text-right text-ink-dim">{row.minutes}</td>
                    <td className="num py-2 pr-4 text-right text-ink-dim">{row.goals}</td>
                    <td className="num py-2 pr-4 text-right text-ink-dim">{row.assists}</td>
                    <td className="num py-2 text-right text-ink-dim">{row.bonus}</td>
                  </tr>
                ))}
                <tr>
                  <td className="py-2 pr-4 text-xs uppercase tracking-wider text-ink-faint">
                    Total
                  </td>
                  <td className="num py-2 pr-4 text-right font-semibold">{totalPoints}</td>
                  <td colSpan={4} />
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {comparisons.length > 0 ? (
        <section className="mt-10">
          <RuleHeading>Compare {player.name} with</RuleHeading>
          <ul className="flex flex-wrap gap-2">
            {comparisons.map((other) => {
              const pair = [player.slug, other.slug].sort().join("-vs-");
              return (
                <li key={other.slug}>
                  <Link
                    href={`/compare/${pair}`}
                    className="inline-flex min-h-[40px] items-center rounded-[8px] border border-border px-3 py-2 text-sm text-ink-dim transition-colors hover:border-border-strong hover:text-ink"
                  >
                    {player.name} or {other.name}?
                  </Link>
                </li>
              );
            })}
          </ul>
        </section>
      ) : null}

      <section className="mt-12">
        <Card className="p-6">
          <h2 className="text-lg font-semibold">
            Does owning {player.name} actually help you win your league?
          </h2>
          <p className="mt-2 leading-relaxed text-ink-dim">
            Expected points is the wrong question. What matters is whether the people
            in <em>your</em> mini-league own him — a player everyone has cannot gain you
            anything, and a player nobody has is the only lever you have when you are
            behind. Paste your league ID and Overtake will tell you which of those this
            is.
          </p>
          <Link
            href="/"
            className="mt-4 inline-flex min-h-[44px] items-center rounded-[8px] bg-you px-5 py-2.5 text-sm font-semibold text-[#06231a] transition-colors hover:bg-[#4ae8a5]"
          >
            Check my league
          </Link>
        </Card>
      </section>
    </div>
  );
}

function Figure({
  value,
  label,
  tone,
}: {
  value: string;
  label: string;
  tone?: "you";
}) {
  return (
    <div>
      <div
        className={`num text-2xl font-semibold ${tone === "you" ? "text-you" : "text-ink"}`}
      >
        {value}
      </div>
      <div className="mt-1 text-xs leading-snug text-ink-faint">{label}</div>
    </div>
  );
}
