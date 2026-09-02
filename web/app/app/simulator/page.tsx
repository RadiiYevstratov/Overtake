import { Simulator } from "@/components/simulator";
import { EmptyState } from "@/components/ui";
import { UpgradePrompt } from "@/components/upgrade-prompt";
import { serverFetchOrNull } from "@/lib/api";
import type { LeagueBoard, Me, TrackedLeague } from "@/lib/types";

export default async function SimulatorPage() {
  const me = (await serverFetchOrNull<Me>("/me"))!;
  if (!me.plan.is_pro) {
    return (
      <UpgradePrompt
        feature="The Overtake Simulator"
        description="Change your captain, try a transfer, and watch your probability against every named rival move in real time. Watching one number rise while another falls is what makes the trade-off real."
        returnTo="/app/simulator"
      />
    );
  }

  const leagues = (await serverFetchOrNull<TrackedLeague[]>("/leagues/")) ?? [];
  if (leagues.length === 0) {
    return (
      <EmptyState title="Add a league first">
        The simulator compares your moves against the specific people in one league.
      </EmptyState>
    );
  }
  const primary = leagues.find((l) => l.is_primary) ?? leagues[0]!;
  const board = await serverFetchOrNull<LeagueBoard>(`/leagues/${primary.league_id}`);

  if (!board) {
    return (
      <EmptyState title="We are still simulating this league">
        Come back in a moment — the first run for a league takes a few seconds.
      </EmptyState>
    );
  }
  if (!me.user.fpl_entry_id) {
    return (
      <EmptyState title="Tell us which manager you are">
        Set your FPL manager ID on the dashboard so we know which squad to change.
      </EmptyState>
    );
  }

  return (
    <>
      <h1 className="text-3xl font-bold tracking-tight">Overtake Simulator</h1>
      <p className="mt-2 max-w-2xl text-ink-dim">
        Try a move and see what it does to your odds against every rival in{" "}
        {primary.name}. Every scenario is scored against the same simulated seasons, so
        the differences are real rather than noise.
      </p>
      <div className="mt-8">
        <Simulator
          leagueId={primary.league_id}
          board={board}
          scenariosPerGameweek={me.limits.scenarios_per_gameweek ?? 0}
        />
      </div>
    </>
  );
}
