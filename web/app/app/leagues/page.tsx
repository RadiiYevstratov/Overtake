import Link from "next/link";

import { LeagueIdForm } from "@/components/league-id-form";
import { UntrackButton } from "@/components/untrack-button";
import { Card, EmptyState, RuleHeading } from "@/components/ui";
import { serverFetchOrNull } from "@/lib/api";
import type { Me, TrackedLeague } from "@/lib/types";

export default async function LeaguesPage() {
  const me = (await serverFetchOrNull<Me>("/me"))!;
  const leagues = (await serverFetchOrNull<TrackedLeague[]>("/leagues/")) ?? [];
  const limit = me.limits.leagues;
  const atLimit = limit !== null && leagues.length >= limit;

  return (
    <>
      <h1 className="text-3xl font-bold tracking-tight">Your leagues</h1>
      <p className="mt-2 text-ink-dim">
        {limit === null
          ? "You can track as many leagues as you are in."
          : `The free plan tracks ${limit} league. Pro tracks as many as you are in.`}
      </p>

      <section className="mt-8">
        <RuleHeading>Tracked</RuleHeading>
        {leagues.length === 0 ? (
          <EmptyState title="You are not tracking any leagues yet">
            Paste a league ID below and we will pull every rival&apos;s squad.
          </EmptyState>
        ) : (
          <ul className="space-y-3">
            {leagues.map((league) => (
              <li key={league.league_id}>
                <Card className="flex flex-wrap items-center justify-between gap-3 p-4">
                  <div className="min-w-0">
                    <Link
                      href={`/l/${league.league_id}`}
                      className="font-medium hover:text-you"
                    >
                      {league.name}
                    </Link>
                    {league.is_primary ? (
                      <span className="ml-2 text-[11px] uppercase tracking-wider text-you">
                        primary
                      </span>
                    ) : null}
                    <p className="num mt-0.5 text-xs text-ink-faint">
                      ID {league.league_id}
                    </p>
                  </div>
                  <UntrackButton leagueId={league.league_id} />
                </Card>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mt-10">
        <RuleHeading>Add another</RuleHeading>
        {atLimit ? (
          <Card className="p-6">
            <p className="text-ink-dim">
              You are at the free plan&apos;s limit of {limit} league. Pro tracks every
              league you are in, and every rival in each of them.
            </p>
            <Link
              href="/pricing"
              className="mt-4 inline-flex min-h-[44px] items-center rounded-[8px] bg-you px-5 py-2.5 text-sm font-semibold text-[#06231a] transition-colors hover:bg-[#4ae8a5]"
            >
              See Pro
            </Link>
          </Card>
        ) : (
          <Card className="p-6">
            <LeagueIdForm />
            <p className="mt-3 text-sm text-ink-faint">
              Open the league page, then press &ldquo;Save league&rdquo;.
            </p>
          </Card>
        )}
      </section>
    </>
  );
}
