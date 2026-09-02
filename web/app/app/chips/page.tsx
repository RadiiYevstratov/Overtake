import Link from "next/link";

import { Badge, Card, EmptyState, RuleHeading } from "@/components/ui";
import { UpgradePrompt } from "@/components/upgrade-prompt";
import { ViewTracker } from "@/components/view-tracker";
import { serverFetchOrNull } from "@/lib/api";
import type { LeagueBoard, Me, TrackedLeague } from "@/lib/types";

/**
 * Chip planning against rivals, not against the field.
 *
 * The value here is asymmetry: a chip your rival has already spent cannot
 * answer a chip you still hold. That is a fact about a named person, which is
 * the only kind of fact this product trades in.
 */
export default async function ChipsPage() {
  const me = (await serverFetchOrNull<Me>("/me"))!;
  if (!me.plan.is_pro) {
    return (
      <UpgradePrompt
        feature="The chip planner"
        description="See which chips each rival has already spent and which they still hold, so you can spend yours where they cannot answer. The highest-stakes decision of the season, made against named people rather than the field."
        returnTo="/app/chips"
      />
    );
  }

  const leagues = (await serverFetchOrNull<TrackedLeague[]>("/leagues/")) ?? [];
  if (leagues.length === 0) {
    return (
      <EmptyState title="Add a league first">
        Chip planning only means something against a specific set of rivals.
      </EmptyState>
    );
  }
  const primary = leagues.find((l) => l.is_primary) ?? leagues[0]!;
  const board = await serverFetchOrNull<LeagueBoard>(`/leagues/${primary.league_id}`);

  if (!board) {
    return (
      <EmptyState title="We are still simulating this league">
        Chip data appears once the first simulation for this league has run.
      </EmptyState>
    );
  }

  const you = board.rows.find((row) => row.is_you);

  return (
    <>
      <ViewTracker
        event="chip_planner_opened"
        props={{ league_id: primary.league_id }}
      />
      <h1 className="text-3xl font-bold tracking-tight">Chip planner</h1>
      <p className="mt-2 max-w-2xl text-ink-dim">
        {primary.name} · Gameweek <span className="num">{board.gameweek}</span>
      </p>

      <section className="mt-8">
        <RuleHeading>Where the leverage is</RuleHeading>
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="p-5">
            <h2 className="font-semibold">If you are behind</h2>
            <p className="mt-2 leading-relaxed text-ink-dim">
              Hold your chips for a gameweek where your rival cannot answer — a double
              gameweek they are light in, or a week their differentials blank. A chip
              played at the same time as everyone else&apos;s buys you nothing against
              the people you are actually racing.
            </p>
          </Card>
          <Card className="p-5">
            <h2 className="font-semibold">If you are ahead</h2>
            <p className="mt-2 leading-relaxed text-ink-dim">
              Match, do not gamble. If the rival behind you plays a chip, playing yours
              in the same gameweek removes most of the swing they were buying. Holding
              a lead is about removing their chances, not creating your own.
            </p>
          </Card>
        </div>
      </section>

      <section className="mt-10">
        <RuleHeading>Who still has what</RuleHeading>
        <Card className="overflow-hidden">
          <div className="scroll-x">
            <table className="w-full border-collapse text-sm">
              <caption className="sr-only">
                Chips remaining for each manager in {primary.name}
              </caption>
              <thead>
                <tr className="border-b border-border text-left text-[11px] uppercase tracking-wider text-ink-faint">
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Manager
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Points
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Chips still available
                  </th>
                </tr>
              </thead>
              <tbody>
                {board.rows.map((row) => (
                  <tr
                    key={row.manager.entry_id}
                    className={`border-b border-border/60 last:border-0 ${
                      row.is_you ? "bg-[#0f1f19]" : ""
                    }`}
                  >
                    <th
                      scope="row"
                      className={`px-4 py-3 text-left font-medium ${
                        row.is_you ? "text-you" : "text-ink"
                      }`}
                    >
                      {row.manager.player_name}
                      {row.is_you ? (
                        <span className="ml-2 text-[11px] uppercase tracking-wider text-you">
                          you
                        </span>
                      ) : null}
                    </th>
                    <td className="num px-4 py-3">{row.manager.total}</td>
                    <td className="px-4 py-3">
                      <span className="text-ink-dim">
                        Chip history is read from the public FPL API each gameweek.
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        <p className="mt-3 text-sm text-ink-faint">
          Chip usage becomes visible for a manager once they have played one. Early in
          a season nobody has, which is why this table is mostly empty in August.
        </p>
      </section>

      {you ? (
        <section className="mt-10">
          <RuleHeading>Next step</RuleHeading>
          <div className="flex flex-wrap gap-2">
            <Link
              href="/app/simulator"
              className="inline-flex min-h-[44px] items-center rounded-[8px] border border-border-strong px-4 py-2.5 text-sm transition-colors hover:border-ink-faint"
            >
              Test a captaincy swing
            </Link>
            <Link
              href={`/l/${primary.league_id}`}
              className="inline-flex min-h-[44px] items-center rounded-[8px] border border-border-strong px-4 py-2.5 text-sm transition-colors hover:border-ink-faint"
            >
              See who is catchable
            </Link>
          </div>
        </section>
      ) : null}

      <div className="mt-8">
        <Badge>V1 feature</Badge>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-faint">
          Per-gameweek chip recommendations against each rival&apos;s fixture exposure
          are the next thing being built here. What is above is real data and real
          strategy; what is not yet here is the automated recommendation.
        </p>
      </div>
    </>
  );
}
