import Link from "next/link";

import { Countdown } from "@/components/countdown";
import { EntryIdPrompt } from "@/components/entry-id-prompt";
import { LeagueTable } from "@/components/league-table";
import { RivalCards } from "@/components/rival-cards";
import {
  Card,
  EmptyState,
  ProvenanceFooter,
  RuleHeading,
  SimulatingState,
  StaleBanner,
} from "@/components/ui";
import { serverFetchOrNull } from "@/lib/api";
import { timestamp } from "@/lib/format";
import type { LeagueBoard, Me, TrackedLeague } from "@/lib/types";

export default async function DashboardPage() {
  const me = (await serverFetchOrNull<Me>("/me"))!;
  const leagues = (await serverFetchOrNull<TrackedLeague[]>("/leagues/")) ?? [];

  if (leagues.length === 0) {
    return (
      <EmptyState
        title="Add your first league"
        action={
          <Link
            href="/"
            className="inline-flex min-h-[44px] items-center rounded-[8px] bg-you px-5 py-2.5 text-sm font-semibold text-[#06231a] transition-colors hover:bg-[#4ae8a5]"
          >
            Find my league
          </Link>
        }
      >
        Paste a league ID and we will pull every rival&apos;s squad, simulate the rest
        of the season, and tell you who you can still catch.
      </EmptyState>
    );
  }

  const primary = leagues.find((l) => l.is_primary) ?? leagues[0]!;
  const board = await serverFetchOrNull<LeagueBoard>(`/leagues/${primary.league_id}`);

  if (!board) return <SimulatingState />;

  const yourRow = board.rows.find((row) => row.is_you);

  return (
    <>
      {board.freshness.is_stale ? (
        <div className="mb-6">
          <StaleBanner
            since={timestamp(
              board.freshness.simulation_computed_at ?? board.freshness.league_synced_at,
            )}
          />
        </div>
      ) : null}

      <div className="flex flex-wrap items-start justify-between gap-6">
        <div className="min-w-0">
          <h1 className="text-3xl font-bold tracking-tight">{board.league.name}</h1>
          <p className="mt-2 text-ink-dim">
            Gameweek <span className="num">{board.gameweek}</span> ·{" "}
            <span className="num">{board.rows.length}</span> managers
          </p>
        </div>
        {board.deadline_utc ? (
          <Countdown deadline={board.deadline_utc} gameweek={board.gameweek + 1} size="large" />
        ) : null}
      </div>

      {!me.user.fpl_entry_id ? (
        <div className="mt-6">
          <EntryIdPrompt rows={board.rows} />
        </div>
      ) : null}

      {yourRow ? (
        <p className="mt-6 text-2xl leading-snug">
          You are{" "}
          <span className="num font-semibold text-you">
            {Math.round(yourRow.p_win * 100)}%
          </span>{" "}
          to win this league, and can still catch{" "}
          <span className="num font-semibold">{board.catchable_count ?? 0}</span> of the
          people above you.
        </p>
      ) : null}

      {me.plan.is_pro ? (
        <Card className="mt-8 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-semibold">Your Deadline Brief is ready</h2>
              <p className="mt-1 text-sm text-ink-dim">
                One move, one risk, one honest case for doing nothing.
              </p>
            </div>
            <Link
              href="/app/brief"
              className="inline-flex min-h-[44px] items-center rounded-[8px] bg-you px-5 py-2.5 text-sm font-semibold text-[#06231a] transition-colors hover:bg-[#4ae8a5]"
            >
              Read the brief
            </Link>
          </div>
        </Card>
      ) : (
        <Card className="mt-8 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-semibold">Get the Deadline Brief before every deadline</h2>
              <p className="mt-1 text-sm text-ink-dim">
                In the app and in your inbox, 36 hours before the deadline.
              </p>
            </div>
            <Link
              href="/pricing"
              className="inline-flex min-h-[44px] items-center rounded-[8px] border border-border-strong px-5 py-2.5 text-sm transition-colors hover:border-ink-faint"
            >
              See Pro
            </Link>
          </div>
        </Card>
      )}

      <section className="mt-10">
        <RuleHeading>The board</RuleHeading>
        <LeagueTable board={board} />
      </section>

      {yourRow ? (
        <section className="mt-10">
          <RuleHeading>Who you can catch</RuleHeading>
          <RivalCards
            leagueId={board.league.id}
            you={yourRow.manager.entry_id}
            rows={board.rows.filter((r) => !r.is_you)}
            isPro={me.plan.is_pro}
            signedIn
          />
        </section>
      ) : null}

      {leagues.length > 1 ? (
        <section className="mt-10">
          <RuleHeading>Your other leagues</RuleHeading>
          <ul className="grid gap-3 sm:grid-cols-2">
            {leagues
              .filter((l) => l.league_id !== primary.league_id)
              .map((league) => (
                <li key={league.league_id}>
                  <Card className="p-4">
                    <Link
                      href={`/l/${league.league_id}`}
                      className="font-medium hover:text-you"
                    >
                      {league.name}
                    </Link>
                  </Card>
                </li>
              ))}
          </ul>
        </section>
      ) : null}

      <div className="mt-10 border-t border-border pt-4">
        <ProvenanceFooter
          nSims={board.provenance.n_sims}
          seed={board.provenance.seed}
          computedAt={timestamp(board.provenance.computed_at)}
          mae={board.provenance.projection_mae}
          maeGameweeks={board.provenance.projection_gameweeks}
        />
      </div>
    </>
  );
}
