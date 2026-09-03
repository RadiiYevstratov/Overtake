import Link from "next/link";

import { RegenerateBriefButton } from "@/components/regenerate-brief-button";
import {
  Badge,
  Card,
  EmptyState,
  ErrorState,
  ProvenanceFooter,
  RuleHeading,
} from "@/components/ui";
import { UpgradePrompt } from "@/components/upgrade-prompt";
import { ViewTracker } from "@/components/view-tracker";
import { ApiError, serverFetch, serverFetchOrNull } from "@/lib/api";
import { timestamp } from "@/lib/format";
import type { Brief, Me, TrackedLeague } from "@/lib/types";

export default async function BriefPage() {
  const me = (await serverFetchOrNull<Me>("/me"))!;
  if (!me.plan.is_pro) {
    return (
      <UpgradePrompt
        feature="The Deadline Brief"
        description="One card before every deadline: the single highest-leverage move for your league position, what it risks, and the honest case for doing nothing. In the app and in your inbox, 36 hours out."
        returnTo="/app/brief"
      />
    );
  }

  const leagues = (await serverFetchOrNull<TrackedLeague[]>("/leagues/")) ?? [];
  if (leagues.length === 0) {
    return (
      <EmptyState title="Add a league first">
        The brief is written about a specific league and a specific set of rivals.
      </EmptyState>
    );
  }
  const primary = leagues.find((l) => l.is_primary) ?? leagues[0]!;

  let brief: Brief;
  try {
    brief = await serverFetch<Brief>(`/leagues/${primary.league_id}/brief`);
  } catch (error) {
    if (error instanceof ApiError) {
      return (
        <ErrorState
          title="We could not write your brief"
          message={error.message}
          errorId={error.errorId}
          action={
            <Link href="/app" className="text-sm text-you underline">
              Back to the dashboard
            </Link>
          }
        />
      );
    }
    throw error;
  }

  const { content } = brief;

  return (
    <>
      <ViewTracker event="brief_viewed" props={{ league_id: primary.league_id }} />

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Deadline Brief</h1>
          <p className="mt-2 text-ink-dim">
            {primary.name} · Gameweek <span className="num">{brief.gameweek}</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge
            tone={
              content.confidence === "high"
                ? "you"
                : content.confidence === "low"
                  ? "warn"
                  : "neutral"
            }
          >
            {content.confidence} confidence
          </Badge>
          <RegenerateBriefButton
            leagueId={primary.league_id}
            used={brief.regenerations_used}
            allowed={brief.regenerations_allowed}
          />
        </div>
      </div>

      {brief.is_fallback ? (
        <div
          role="status"
          className="mt-6 rounded-[8px] border border-border bg-surface px-4 py-3 text-sm text-ink-dim"
        >
          {content.note ??
            "This brief was written straight from the simulation without the AI layer. The numbers are the same ones it would have used."}
        </div>
      ) : null}

      {/* One card. One recommendation. Never a menu of ten options — the
          product's job is to decide, not to present. */}
      <Card className="mt-6 p-6 sm:p-8">
        <h2 className="text-2xl font-semibold leading-snug sm:text-3xl">
          {content.headline}
        </h2>

        <div className="mt-8">
          <RuleHeading>The move</RuleHeading>
          <p className="text-xl font-medium text-ink">{content.primary_move.summary}</p>
          <p className="mt-3 leading-relaxed text-ink-dim">
            {content.primary_move.reasoning}
          </p>
        </div>

        <div className="mt-8">
          <RuleHeading>The risk</RuleHeading>
          <p className="leading-relaxed text-rival">{content.risk}</p>
        </div>

        <div className="mt-8">
          <RuleHeading>The case for doing nothing</RuleHeading>
          <p className="leading-relaxed text-ink-dim">{content.do_nothing_case}</p>
        </div>

        <div className="mt-8 flex flex-wrap gap-2">
          <Link
            href="/app/simulator"
            className="inline-flex min-h-[44px] items-center rounded-[8px] border border-border-strong px-4 py-2.5 text-sm transition-colors hover:border-ink-faint"
          >
            Try a different move
          </Link>
          <Link
            href={`/l/${primary.league_id}`}
            className="inline-flex min-h-[44px] items-center rounded-[8px] border border-border-strong px-4 py-2.5 text-sm transition-colors hover:border-ink-faint"
          >
            See the league board
          </Link>
        </div>
      </Card>

      <div className="mt-6">
        <ProvenanceFooter
          nSims={brief.provenance.n_sims}
          seed={brief.provenance.seed}
          computedAt={timestamp(brief.generated_at)}
          mae={brief.provenance.projection_mae}
          maeGameweeks={brief.provenance.projection_gameweeks}
        />
        <p className="mt-2 text-[11px] leading-relaxed text-ink-faint">
          {brief.is_fallback
            ? "Written straight from the simulation, with no AI involved. Every figure above is a number the simulation produced."
            : "Written by AI from the simulation output above. Every number in it is checked against that simulation before you see it; if a check fails, we show you the numbers without the prose rather than guess."}
        </p>
      </div>
    </>
  );
}
