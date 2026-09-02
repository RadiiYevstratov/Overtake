import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { AhaTracker } from "@/components/aha-tracker";
import { Countdown } from "@/components/countdown";
import { ShareButton } from "@/components/share-button";
import {
  Card,
  ErrorState,
  ProvenanceFooter,
  RuleHeading,
  SimulatingState,
  Stat,
  cx,
} from "@/components/ui";
import { ViewTracker } from "@/components/view-tracker";
import { ApiError, serverFetch, serverFetchOrNull } from "@/lib/api";
import { money, signedInt, signedPoints, timestamp, varianceCopy } from "@/lib/format";
import type { Differential, Dossier, Me } from "@/lib/types";

type Params = Promise<{ leagueId: string; entryId: string }>;
type Search = Promise<{ you?: string }>;

export const metadata: Metadata = { robots: { index: false, follow: false } };

export default async function DossierPage({
  params,
  searchParams,
}: {
  params: Params;
  searchParams: Search;
}) {
  const { leagueId, entryId } = await params;
  const { you } = await searchParams;

  const league = Number.parseInt(leagueId, 10);
  const rival = Number.parseInt(entryId, 10);
  if (!Number.isSafeInteger(league) || !Number.isSafeInteger(rival)) notFound();

  const me = await serverFetchOrNull<Me>("/me");
  const yourEntry = you ?? (me?.user.fpl_entry_id ? String(me.user.fpl_entry_id) : null);

  if (!yourEntry) {
    return (
      <Shell>
        <ErrorState
          title="We need to know which manager you are"
          message="Head back to the league board and pick your name, and we can work out the gap."
          action={
            <Link href={`/l/${league}`} className="text-sm text-you underline">
              Back to the league board
            </Link>
          }
        />
      </Shell>
    );
  }

  let dossier: Dossier;
  try {
    dossier = await serverFetch<Dossier>(
      `/leagues/${league}/rivals/${rival}/dossier?you=${encodeURIComponent(yourEntry)}`,
    );
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
            message={error.message}
            errorId={error.errorId}
            action={
              <Link href={`/l/${league}`} className="text-sm text-you underline">
                Back to the league board
              </Link>
            }
          />
        </Shell>
      );
    }
    throw error;
  }

  const { odds, rival: them, you: mine } = dossier;
  const behind = odds.gap_now < 0;

  return (
    <Shell>
      <ViewTracker
        event="dossier_viewed"
        props={{ league_id: league, rival: rival }}
      />

      <Link
        href={`/l/${league}?entry=${yourEntry}`}
        className="text-sm text-ink-dim transition-colors hover:text-ink"
      >
        ← {dossier.league.name}
      </Link>

      {/* --------------------------------------------------------- header */}
      <header className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-3xl font-bold uppercase tracking-tight sm:text-4xl">
            <span className="text-you">You</span>{" "}
            <span className="text-ink-faint">vs</span>{" "}
            <span className="text-rival">{them.player_name}</span>
          </h1>
          <p className="mt-2 truncate text-ink-dim">
            {mine.team_name} <span className="text-ink-faint">against</span>{" "}
            {them.team_name}
          </p>
        </div>
        {dossier.deadline_utc ? (
          <div className="text-right">
            <div className="text-[11px] uppercase tracking-wider text-ink-faint">
              GW{dossier.gameweek}
            </div>
            <Countdown deadline={dossier.deadline_utc} size="large" />
          </div>
        ) : null}
      </header>

      {/* ---------------------------------------------------- the numbers */}
      <Card className="mt-6 p-6">
        <div className="grid grid-cols-3 gap-4 text-center">
          <Stat
            value={`${Math.round(odds.p_above * 100)}%`}
            label="to finish above"
            tone={odds.p_above >= 0.5 ? "you" : "rival"}
          />
          <Stat
            value={signedInt(odds.gap_now)}
            label={behind ? "points behind" : "points ahead"}
          />
          <Stat value={dossier.gameweeks_left} label="gameweeks left" />
        </div>
      </Card>

      {/* ------------------------------------------------- what it takes */}
      <section className="mt-10">
        <RuleHeading>What it takes</RuleHeading>
        {behind ? (
          <p className="text-2xl leading-snug sm:text-3xl">
            <span className="num font-semibold text-you">
              +{odds.points_per_gw_needed.toFixed(1)}
            </span>{" "}
            points per gameweek, every gameweek.
          </p>
        ) : (
          <p className="text-2xl leading-snug sm:text-3xl">
            You are ahead. Holding a{" "}
            <span className="num font-semibold text-you">{odds.gap_now}</span>-point lead
            for {dossier.gameweeks_left} more gameweeks.
          </p>
        )}
        <p className="mt-3 text-ink-dim">
          {varianceCopy(odds.variance)}.{" "}
          {odds.variance === "seek"
            ? "Copying what they own locks in the gap — that is the trap."
            : odds.variance === "suppress"
              ? "Owning what they own removes their chances to gain on you."
              : "Small edges decide this one."}
        </p>
        <p className="num mt-4 text-sm text-ink-faint">
          Simulated range: {signedPoints(dossier.odds.gap_p10, 0)} to{" "}
          {signedPoints(dossier.odds.gap_p90, 0)} points at the end of the season
          (10th–90th percentile).
        </p>
      </section>

      {/* --------------------------------------------- where the gap is */}
      <section className="mt-10">
        <RuleHeading>Where the gap is</RuleHeading>
        <div className="grid gap-4 md:grid-cols-2">
          <DifferentialList
            title={`${them.player_name} owns, you don't`}
            tone="rival"
            rows={dossier.their_differentials}
          />
          <DifferentialList
            title={`You own, ${them.player_name} doesn't`}
            tone="you"
            rows={dossier.your_differentials}
          />
        </div>
        <p className="mt-4 text-lg">
          Net differential swing:{" "}
          <span
            className={cx(
              "num font-semibold",
              dossier.net_differential_swing >= 0 ? "text-you" : "text-rival",
            )}
          >
            {signedPoints(dossier.net_differential_swing)}
          </span>{" "}
          <span className="text-ink-dim">
            expected points over {dossier.gameweeks_left} gameweeks
          </span>
        </p>
      </section>

      {/* This is the point where the value has landed. */}
      <AhaTracker leagueId={league} rivalId={rival} />

      {/* ----------------------------------------------- their behaviour */}
      <section className="mt-10">
        <RuleHeading>{them.player_name}&apos;s pattern</RuleHeading>
        <Card className="p-5">
          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <h3 className="text-lg font-semibold text-ink">
              {dossier.profile.label}
            </h3>
            {dossier.profile.is_provisional ? (
              <span className="text-xs text-ink-faint">
                (provisional — only{" "}
                <span className="num">{dossier.profile.gameweeks_observed}</span>{" "}
                gameweeks watched so far)
              </span>
            ) : null}
          </div>
          <p className="mt-2 text-ink-dim">{dossier.profile.blurb}</p>
          <dl className="mt-5 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
            <ProfileStat
              label="Hits taken"
              value={`${dossier.profile.hit_rate.toFixed(2)}/GW`}
            />
            <ProfileStat
              label="Transfers"
              value={`${dossier.profile.transfers_per_gw.toFixed(2)}/GW`}
            />
            <ProfileStat
              label="Template overlap"
              value={`${Math.round(dossier.profile.template_score * 100)}%`}
            />
            <ProfileStat
              label="Points on bench"
              value={`${dossier.profile.bench_waste.toFixed(1)}/GW`}
            />
          </dl>
          <p className="mt-4 text-xs text-ink-faint">
            Built from{" "}
            <span className="num">{dossier.profile.gameweeks_observed}</span> gameweeks
            of their public transfer history.
          </p>
        </Card>
      </section>

      {/* -------------------------------------------------- the move */}
      <section className="mt-10">
        <RuleHeading>The move</RuleHeading>
        {dossier.move ? (
          <Card className="border-you-dim p-6">
            <h3 className="text-2xl font-semibold text-ink">{dossier.move.label}</h3>
            <p className="mt-3 text-lg">
              <span className="num text-ink-dim">
                {Math.round(dossier.move.p_above_before * 100)}%
              </span>{" "}
              <span aria-hidden="true" className="text-ink-faint">
                →
              </span>{" "}
              <span className="num font-semibold text-you">
                {Math.round(dossier.move.p_above_after * 100)}%
              </span>{" "}
              <span className="text-ink-dim">
                to finish above {them.player_name}
              </span>
            </p>
            <p className="mt-4 text-ink-dim">
              <span className="text-rival">Downside:</span> if it does not come off,
              that is{" "}
              <span className="num">
                {signedPoints(dossier.move.downside_p10)}
              </span>{" "}
              against your current captain.
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              <Link
                href="/app/simulator"
                className="inline-flex min-h-[44px] items-center rounded-[8px] border border-border-strong px-4 py-2.5 text-sm transition-colors hover:border-ink-faint"
              >
                Try a different move
              </Link>
              <ShareButton
                leagueId={league}
                leagueName={dossier.league.name}
                entryId={mine.entry_id}
                rivalName={them.player_name}
                probability={odds.p_above}
              />
            </div>
          </Card>
        ) : (
          <LockedMove
            reason={dossier.lock_reason}
            rivalName={them.player_name}
            signedIn={Boolean(me)}
            returnTo={`/l/${league}/vs/${rival}?you=${yourEntry}`}
          />
        )}
      </section>

      <div className="mt-10 border-t border-border pt-4">
        <ProvenanceFooter
          nSims={dossier.provenance.n_sims}
          seed={dossier.provenance.seed}
          computedAt={timestamp(dossier.provenance.computed_at)}
          mae={dossier.provenance.projection_mae}
          maeGameweeks={dossier.provenance.projection_gameweeks}
        />
      </div>

      {/* Sticky on mobile: the move is what the user came for. */}
      <div className="sticky bottom-0 -mx-4 mt-8 border-t border-border bg-base/95 px-4 py-3 backdrop-blur sm:hidden">
        <ShareButton
          leagueId={league}
          leagueName={dossier.league.name}
          entryId={mine.entry_id}
          rivalName={them.player_name}
          probability={odds.p_above}
          variant="primary"
        />
      </div>
    </Shell>
  );
}

function DifferentialList({
  title,
  rows,
  tone,
}: {
  title: string;
  rows: Differential[];
  tone: "you" | "rival";
}) {
  return (
    <Card className="p-5">
      <h3
        className={cx(
          "text-sm font-semibold",
          tone === "you" ? "text-you" : "text-rival",
        )}
      >
        {title}
      </h3>
      {rows.length === 0 ? (
        <p className="mt-3 text-sm text-ink-dim">
          Nothing — your squads overlap completely here.
        </p>
      ) : (
        <ul className="mt-3 space-y-2">
          {rows.map((row) => (
            <li
              key={row.player_id}
              className="flex items-baseline justify-between gap-3 text-sm"
            >
              <span className="min-w-0 truncate">
                <span className="text-ink">{row.name}</span>{" "}
                <span className="text-ink-faint">
                  {row.team} · {row.position} · {money(row.price)}
                </span>
              </span>
              <span className="num shrink-0 text-ink-dim">
                {row.ep_remaining.toFixed(1)} xPts
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function ProfileStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-ink-faint">{label}</dt>
      <dd className="num mt-0.5 text-ink">{value}</dd>
    </div>
  );
}

function LockedMove({
  reason,
  rivalName,
  signedIn,
  returnTo,
}: {
  reason: string | null;
  rivalName: string;
  signedIn: boolean;
  returnTo: string;
}) {
  return (
    <Card className="p-6">
      <p className="text-lg leading-relaxed text-ink">
        {reason ??
          `See the single move that most improves your odds against ${rivalName}.`}
      </p>
      <div className="mt-5 flex flex-wrap items-center gap-3">
        <Link
          href={signedIn ? "/pricing" : `/signin?next=${encodeURIComponent(returnTo)}`}
          className="inline-flex min-h-[44px] items-center rounded-[8px] bg-you px-5 py-2.5 text-sm font-semibold text-[#06231a] transition-colors hover:bg-[#4ae8a5]"
        >
          {signedIn
            ? `Unlock the move against ${rivalName}`
            : "Create a free account"}
        </Link>
        {signedIn ? (
          <span className="text-sm text-ink-faint">
            €4.99 a month · €29.99 for the season
          </span>
        ) : (
          <span className="text-sm text-ink-faint">
            One rival dossier is free, every season
          </span>
        )}
      </div>
    </Card>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">{children}</div>;
}
