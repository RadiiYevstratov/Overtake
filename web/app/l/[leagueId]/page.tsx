import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { EntryPicker } from "@/components/entry-picker";
import { LeagueTable } from "@/components/league-table";
import { RivalCards } from "@/components/rival-cards";
import { ShareButton } from "@/components/share-button";
import { TrackLeagueButton } from "@/components/track-league-button";
import {
  Card,
  ErrorState,
  ProvenanceFooter,
  RuleHeading,
  SimulatingState,
  StaleBanner,
} from "@/components/ui";
import { ViewTracker } from "@/components/view-tracker";
import { ApiError, serverFetch, serverFetchOrNull } from "@/lib/api";
import { timestamp } from "@/lib/format";
import type { LeagueBoard, Me } from "@/lib/types";

type Params = Promise<{ leagueId: string }>;
type Search = Promise<{ entry?: string }>;

/**
 * League pages are noindex by design (10-growth-and-seo.md §1.1): they contain
 * other people's team names and are of no value to a stranger. They are fully
 * shareable by URL — shareability and indexability are different goals.
 */
export async function generateMetadata({
  params,
}: {
  params: Params;
}): Promise<Metadata> {
  const { leagueId } = await params;
  const board = await serverFetchOrNull<LeagueBoard>(`/leagues/${leagueId}`);
  const name = board?.league.name ?? "Your league";
  return {
    title: `${name} — league odds`,
    description: `Who can still be caught in ${name}, and what it takes.`,
    robots: { index: false, follow: false },
  };
}

export default async function LeagueBoardPage({
  params,
  searchParams,
}: {
  params: Params;
  searchParams: Search;
}) {
  const { leagueId } = await params;
  const { entry } = await searchParams;

  const id = Number.parseInt(leagueId, 10);
  if (!Number.isSafeInteger(id) || id <= 0) notFound();

  const me = await serverFetchOrNull<Me>("/me");
  const you = entry ?? (me?.user.fpl_entry_id ? String(me.user.fpl_entry_id) : null);
  const query = you ? `?entry=${encodeURIComponent(you)}` : "";

  let board: LeagueBoard;
  try {
    board = await serverFetch<LeagueBoard>(`/leagues/${id}${query}`);
  } catch (error) {
    if (error instanceof ApiError) {
      if (error.isNotFound) notFound();
      if (error.isNotSimulatedYet) {
        return (
          <Shell>
            <SimulatingState />
          </Shell>
        );
      }
      return (
        <Shell>
          <ErrorState
            title="We could not read that league"
            message={error.message}
            errorId={error.errorId}
            action={
              <Link href="/" className="text-sm text-you underline">
                Try a different league ID
              </Link>
            }
          />
        </Shell>
      );
    }
    throw error;
  }

  const yourRow = board.rows.find((row) => row.is_you);
  const rivals = board.rows.filter((row) => !row.is_you);
  const catchable = board.catchable_count ?? 0;
  const behind = rivals.filter((row) => (row.odds_vs_you?.gap_now ?? 0) < 0).length;

  return (
    <Shell>
      <ViewTracker event="league_board_viewed" props={{ league_id: id }} />

      {board.freshness.is_stale ? (
        <div className="mb-6">
          <StaleBanner
            since={timestamp(
              board.freshness.simulation_computed_at ??
                board.freshness.league_synced_at,
            )}
          />
        </div>
      ) : null}

      <header className="mb-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
              {board.league.name}
            </h1>
            <p className="mt-2 text-ink-dim">
              Gameweek <span className="num">{board.gameweek}</span> ·{" "}
              <span className="num">{board.rows.length}</span> managers
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <ShareButton
              leagueId={id}
              leagueName={board.league.name}
              entryId={yourRow?.manager.entry_id ?? null}
            />
            {me ? <TrackLeagueButton leagueId={id} /> : null}
          </div>
        </div>

        {yourRow ? (
          <p className="mt-6 text-2xl leading-snug sm:text-3xl">
            {catchable > 0 ? (
              <>
                You can realistically still catch{" "}
                <span className="num font-semibold text-you">{catchable}</span> of{" "}
                <span className="num">{behind}</span> above you.
              </>
            ) : behind === 0 ? (
              <>
                You are top of{" "}
                <span className="font-semibold">{board.league.name}</span>. The job now
                is not losing it.
              </>
            ) : (
              <>
                Nobody above you is realistically catchable on current form — so the
                target is holding your place, not chasing.
              </>
            )}
          </p>
        ) : (
          <div className="mt-6">
            <EntryPicker leagueId={id} rows={board.rows} />
          </div>
        )}
      </header>

      <LeagueTable board={board} />

      {yourRow ? (
        <section className="mt-12">
          <RuleHeading>Who you can catch</RuleHeading>
          <RivalCards
            leagueId={id}
            you={yourRow.manager.entry_id}
            rows={rivals}
            isPro={me?.plan.is_pro ?? false}
            signedIn={Boolean(me)}
          />
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

      {!me ? (
        <Card className="mt-8 p-6">
          <h2 className="text-lg font-semibold">
            Want this before every deadline?
          </h2>
          <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink-dim">
            A free account saves this league and sends you the Deadline Brief. No
            password to remember — we email you a link.
          </p>
          <Link
            href={`/signin?next=${encodeURIComponent(`/l/${id}${query}`)}`}
            className="mt-4 inline-flex min-h-[44px] items-center rounded-[8px] bg-you px-5 py-2.5 text-sm font-semibold text-[#06231a] transition-colors hover:bg-[#4ae8a5]"
          >
            Save this league
          </Link>
        </Card>
      ) : null}
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">{children}</div>
  );
}
