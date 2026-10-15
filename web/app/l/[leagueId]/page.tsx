import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { AutoRefresh } from "@/components/auto-refresh";
import { EntryPicker } from "@/components/entry-picker";
import { LeagueTable } from "@/components/league-table";
import { RivalCards } from "@/components/rival-cards";
import { RivalPicker } from "@/components/rival-picker";
import { ShareButton } from "@/components/share-button";
import { TrackLeagueButton } from "@/components/track-league-button";
import {
  Card,
  ErrorState,
  ProvenanceBanners,
  ProvenanceFooter,
  RuleHeading,
  SimulatingState,
  StaleBanner,
} from "@/components/ui";
import { ViewTracker } from "@/components/view-tracker";
import {
  ApiError,
  serverFetch,
  serverFetchOptional,
  serverFetchOrNull,
  supportReference,
} from "@/lib/api";
import { hasSession } from "@/lib/session";
import { dossierAccess, proOnlyRivals } from "@/lib/dossier-access";
import { timestamp } from "@/lib/format";
import type { LeagueBoard, Me } from "@/lib/types";

type Params = Promise<{ leagueId: string }>;
type Search = Promise<{ entry?: string; utm_source?: string }>;

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
  // The title is decoration; the page itself reports any failure properly.
  const board = await serverFetchOptional(() =>
    serverFetchOrNull<LeagueBoard>(`/leagues/${leagueId}`),
  );
  const name = board?.league?.name ?? "Your league";
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
  const { entry, utm_source: source } = await searchParams;

  const id = Number.parseInt(leagueId, 10);
  if (!Number.isSafeInteger(id) || id <= 0) notFound();

  const me = (await hasSession()) ? await serverFetchOrNull<Me>("/me") : null;
  // `entry` is the viewpoint a signed-out visitor picked for themselves. Share
  // links used to carry the sharer's, so a link tagged as a share never
  // chooses who "you" are — the recipient picks, or their account decides. The
  // API then prefers the account whenever its manager is in this league.
  const requested = source === "share" ? undefined : entry;
  const you = requested ?? (me?.user?.fpl_entry_id ? String(me.user.fpl_entry_id) : null);
  const query = you ? `?entry=${encodeURIComponent(you)}` : "";

  let board: LeagueBoard;
  try {
    board = await serverFetch<LeagueBoard>(`/leagues/${id}${query}`);
  } catch (error) {
    if (error instanceof ApiError) {
      // The site's not-found page already explains an unreadable league ID and
      // offers the form again — and it keeps the 404 status, which a custom
      // message rendered here would lose.
      if (error.isNotFound) notFound();
      if (error.isNotSimulatedYet) {
        // A first visit reads the league from FPL behind this screen, so it
        // keeps asking until the board exists — see components/auto-refresh.
        return (
          <Shell>
            <SimulatingState />
            <AutoRefresh />
          </Shell>
        );
      }
      if (error.code === "LEAGUE_TOO_LARGE") {
        // A product rule, not a failure: no red, no reference to quote.
        return (
          <Shell>
            <LeagueTooLarge message={error.message} />
          </Shell>
        );
      }
      return (
        <Shell>
          <ErrorState
            title="We could not read that league"
            message={error.message}
            errorId={supportReference(error)}
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
  const access = dossierAccess(me, id);
  const catchable = board.catchable_count ?? 0;
  // Counted by points in the table shown, so the sentence agrees with the table.
  const above =
    board.rivals_above ??
    rivals.filter((row) => yourRow && row.manager.total > yourRow.manager.total).length;
  const unrated = board.rivals_above_without_odds ?? 0;
  const oddsCurrent = board.freshness.odds_match_standings !== false;
  const provisional = board.provenance.history_complete === false;

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
            apiOk={board.freshness.fpl_api_ok}
          />
          {/* Viewing queued a re-read of this league; show it when it lands. */}
          {board.freshness.fpl_api_ok ? <AutoRefresh everyMs={5000} maxTries={6} /> : null}
        </div>
      ) : null}

      <ProvenanceBanners oddsCurrent={oddsCurrent} provisional={provisional} />

      <header className="mb-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
              {board.league.name}
            </h1>
            <p className="mt-2 text-ink-dim">
              Gameweek <span className="num">{board.gameweek}</span> standings ·{" "}
              <span className="num">{board.rows.length}</span> managers
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <ShareButton leagueId={id} leagueName={board.league.name} />
            {me ? <TrackLeagueButton leagueId={id} /> : null}
          </div>
        </div>

        {yourRow ? (
          <>
            <p className="mt-6 text-2xl leading-snug sm:text-3xl">
              {above === 0 ? (
                <>
                  You are top of{" "}
                  <span className="font-semibold">{board.league.name}</span>. The job
                  now is not losing it.
                </>
              ) : catchable > 0 ? (
                <>
                  <span className="num font-semibold text-you">{catchable}</span> of the{" "}
                  <span className="num">{above}</span>{" "}
                  {above === 1 ? "manager" : "managers"} above you{" "}
                  {catchable === 1 ? "is" : "are"} still realistically catchable.
                </>
              ) : (
                <>
                  Nobody above you is realistically catchable on current form — so the
                  target is holding your place, not chasing.
                </>
              )}
            </p>
            {above > 0 ? (
              <p className="mt-2 text-sm text-ink-faint">
                Realistically catchable means at least a 1-in-20 (5%) chance of finishing
                above them.
                {unrated > 0
                  ? ` We have no odds yet for ${unrated} of the ${above} — their squad has not been read.`
                  : ""}
              </p>
            ) : null}
          </>
        ) : (
          <div className="mt-6">
            <EntryPicker leagueId={id} rows={board.rows} />
          </div>
        )}
      </header>

      <LeagueTable board={board} />

      {yourRow ? (
        <section className="mt-12">
          <RuleHeading>The rivals who matter</RuleHeading>
          <RivalCards
            leagueId={id}
            you={yourRow.manager.entry_id}
            rows={rivals}
            isPro={me?.plan?.is_pro ?? false}
            signedIn={Boolean(me)}
            freeRivals={access.freeRivals}
            canChoose={access.canChoose}
          />
          <RivalPicker
            leagueId={id}
            you={yourRow.manager.entry_id}
            rows={rivals}
            proOnly={proOnlyRivals(access, rivals)}
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
          runId={board.provenance.run_id}
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

function LeagueTooLarge({ message }: { message: string }) {
  return (
    <Card className="p-6">
      <h1 className="text-2xl font-bold tracking-tight">That league is bigger than a mini-league</h1>
      <p className="mt-3 leading-relaxed text-ink-dim">{message}</p>
      <p className="mt-3 leading-relaxed text-ink-dim">
        Overtake works on classic leagues of up to 200 managers — the people you
        actually play against. Paste the ID of your own mini-league instead.
      </p>
      <div className="mt-5 flex flex-wrap gap-4 text-sm">
        <Link href="/" className="text-you underline">
          Try a different league ID
        </Link>
        <Link href="/how-to/find-your-fpl-league-id" className="text-ink-dim underline">
          Where do I find my league ID?
        </Link>
      </div>
    </Card>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">{children}</div>
  );
}
