"use client";

import { useState } from "react";

import { Badge, Button, Card, RuleHeading, cx } from "@/components/ui";
import { ApiError, clientFetch, track } from "@/lib/api";
import { money } from "@/lib/format";
import type { LeagueBoard, ScenarioResult, Squad, SquadPlayer } from "@/lib/types";

/**
 * The interaction is the value: watching one probability rise while another
 * falls is what makes a trade-off real.
 *
 * Tap-to-select on every screen size rather than drag-and-drop. A broken drag
 * on touch is worse than no drag at all, and a list of buttons is fully
 * keyboard-operable without any extra work.
 */
export function Simulator({
  leagueId,
  board,
  initialSquad,
  squadError,
}: {
  leagueId: number;
  board: LeagueBoard;
  /** Rendered with the page. Fetching it after mount left it on a skeleton forever
   *  on a full page load: the response arrived but never reached the state. */
  initialSquad: Squad | null;
  squadError: string | null;
}) {
  const squad = initialSquad;
  const loadError = squadError;
  const [captain, setCaptain] = useState<number | null>(
    initialSquad?.players.find((p) => p.is_captain)?.player_id ?? null,
  );
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // The server's count, not this visit's clicks: scenarios run on an earlier
  // visit, or in another tab, come out of the same allowance.
  const [used, setUsed] = useState(initialSquad?.scenarios_used ?? 0);

  const currentCaptain = squad?.players.find((p) => p.is_captain) ?? null;
  const changed = captain !== null && captain !== currentCaptain?.player_id;
  const allowed = squad?.scenarios_allowed ?? null;
  const remaining = allowed === null ? null : Math.max(0, allowed - used);
  const exhausted = remaining === 0;

  async function run() {
    if (captain === null) return;
    setBusy(true);
    setError(null);
    track("simulator_run", { league_id: leagueId });
    try {
      const response = await clientFetch<ScenarioResult>(
        `/leagues/${leagueId}/simulate`,
        {
          method: "POST",
          body: JSON.stringify({ moves: [{ type: "captain", captain }] }),
        },
      );
      setResult(response);
      setUsed((n) => response.scenarios_used ?? n + 1);
    } catch (err) {
      if (err instanceof ApiError && err.code === "SCENARIO_LIMIT" && allowed !== null) {
        // The allowance ran out elsewhere; the counter below says so plainly.
        setUsed(allowed);
      } else {
        setError(err instanceof ApiError ? err.message : "That scenario could not run.");
      }
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setCaptain(currentCaptain?.player_id ?? null);
    setResult(null);
    setError(null);
  }

  const scenario = result?.scenarios[0];
  const rivals = board.rows.filter((row) => !row.is_you && row.odds_vs_you);
  const summary =
    scenario && squad ? summarise(scenario, squad.players, currentCaptain, rivals) : null;

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,24rem)_1fr]">
      {/* ------------------------------------------------------- squad */}
      <Card className="h-fit p-5">
        <RuleHeading>Your squad</RuleHeading>

        {loadError || !squad ? (
          <p role="alert" className="text-sm text-rival">
            {loadError ?? "We could not load your squad."}
          </p>
        ) : (
          <>
            <p className="mb-3 text-sm text-ink-dim">
              Tap one of your starting eleven to captain them for Gameweek{" "}
              <span className="num">{squad.gameweek}</span>. The doubled score is the
              biggest single lever you have.
            </p>
            <ul className="space-y-1" role="radiogroup" aria-label="Choose your captain">
              {squad.players.map((player) => (
                <li key={player.player_id}>
                  <PlayerRow
                    player={player}
                    selected={captain === player.player_id}
                    isCurrent={player.player_id === currentCaptain?.player_id}
                    onSelect={() => setCaptain(player.player_id)}
                  />
                </li>
              ))}
            </ul>

            <div className="mt-4 flex gap-2">
              <Button onClick={run} disabled={!changed || busy || exhausted} className="flex-1">
                {busy ? "Simulating…" : "Run this scenario"}
              </Button>
              {result ? (
                <Button variant="secondary" onClick={reset}>
                  Reset
                </Button>
              ) : null}
            </div>

            {exhausted ? (
              <p className="mt-3 text-xs text-warn">
                You have used all <span className="num">{allowed}</span> scenarios this
                gameweek. More after the next deadline.
              </p>
            ) : (
              <p className="mt-3 text-xs text-ink-faint">
                {remaining === null ? (
                  "Unlimited scenarios"
                ) : (
                  <>
                    <span className="num">{remaining}</span> scenarios left this gameweek
                  </>
                )}
                {!changed && !result ? " · pick a different captain to run one" : ""}
              </p>
            )}

            {error ? (
              <p role="alert" className="mt-3 text-sm text-rival">
                {error}
              </p>
            ) : null}
          </>
        )}
      </Card>

      {/* ------------------------------------------------------ results */}
      <div>
        <RuleHeading>
          {scenario ? `If you ${scenario.label.toLowerCase()}` : "Your odds right now"}
        </RuleHeading>

        {/* One sentence for the whole league before the rival-by-rival detail:
            28 small changes are hard to add up in your head. */}
        {summary && squad ? (
          <Card className="mb-4 p-5">
            <p className="text-sm text-ink-dim">
              {summary.newCaptain} instead of {summary.oldCaptain}
            </p>
            <p className="mt-1 text-lg text-ink">
              <span
                className={cx(
                  "num font-semibold",
                  summary.points > 0 ? "text-you" : summary.points < 0 ? "text-rival" : "",
                )}
              >
                {summary.points > 0 ? "+" : summary.points < 0 ? "−" : ""}
                {Math.abs(summary.points).toFixed(1)}
              </span>{" "}
              expected points in Gameweek <span className="num">{squad.gameweek}</span>
            </p>
            <p className="mt-2 text-sm leading-relaxed text-ink-dim">
              {Math.abs(summary.average) < 0.0005 ? (
                "Your chance of finishing above your rivals barely moves on average"
              ) : (
                <>
                  Your chance of finishing above a rival{" "}
                  {summary.average > 0 ? "rises" : "falls"} by{" "}
                  <span className="num text-ink">
                    {Math.abs(summary.average * 100).toFixed(1)}
                  </span>{" "}
                  percentage points on average
                </>
              )}
              {" — "}better against <span className="num text-ink">{summary.better}</span>,
              worse against <span className="num text-ink">{summary.worse}</span>
              {summary.same > 0 ? (
                <>
                  , about the same against <span className="num text-ink">{summary.same}</span>
                </>
              ) : null}
              .
            </p>
          </Card>
        ) : null}

        <ul className="space-y-2">
          {rivals.map((row) => {
            const odds = row.odds_vs_you!;
            const key = String(row.manager.entry_id);
            const after = scenario?.p_above[key];
            const delta = scenario?.delta[key];
            const shown = after ?? odds.p_above;

            return (
              <li key={row.manager.entry_id}>
                <Card className="flex items-center gap-3 p-4 sm:gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="truncate font-medium">
                      {row.manager.player_name}
                    </div>
                    <div className="truncate text-sm text-ink-dim">
                      {row.manager.team_name}
                    </div>
                  </div>

                  <div className="hidden w-40 shrink-0 sm:block">
                    <div
                      className="h-2 overflow-hidden rounded-full bg-surface-2"
                      role="img"
                      aria-label={`${Math.round(shown * 100)} percent`}
                    >
                      <div
                        className={cx(
                          "h-full transition-[width] duration-500",
                          shown >= 0.5 ? "bg-you" : "bg-rival",
                        )}
                        style={{ width: `${Math.max(2, Math.round(shown * 100))}%` }}
                      />
                    </div>
                  </div>

                  <div className="w-24 shrink-0 text-right sm:w-28">
                    <div
                      className={cx(
                        "num text-xl font-semibold",
                        shown >= 0.6
                          ? "text-you"
                          : shown <= 0.25
                            ? "text-rival"
                            : "text-ink",
                      )}
                    >
                      {/* A decimal once a scenario runs: most moves shift a rival by
                          less than a point, which rounding would hide entirely. */}
                      {scenario ? (shown * 100).toFixed(1) : Math.round(shown * 100)}%
                    </div>
                    {delta !== undefined ? (
                      <div className="mt-0.5 text-xs">
                        <Change before={odds.p_above} delta={delta} />
                      </div>
                    ) : null}
                  </div>
                </Card>
              </li>
            );
          })}
        </ul>

        <p className="mt-4 text-sm leading-relaxed text-ink-faint">
          Changes are in percentage points: going from 43.0% to 42.5% is half a point.
          Every scenario is scored against the same 20,000 simulated seasons as the
          baseline, so a change that size is a real difference, not sampling noise.
        </p>
      </div>
    </div>
  );
}

/** Smaller than this, a change is inside sampling noise and counts as "the same". */
const NOISE = 0.005;

interface Summary {
  newCaptain: string;
  oldCaptain: string;
  /** Expected points this change of armband adds (or costs) in the gameweek. */
  points: number;
  /** Mean change, as a probability, in the chance of finishing above each rival. */
  average: number;
  better: number;
  worse: number;
  same: number;
}

function summarise(
  scenario: ScenarioResult["scenarios"][number],
  players: SquadPlayer[],
  currentCaptain: SquadPlayer | null,
  rivals: LeagueBoard["rows"],
): Summary | null {
  const chosen = players.find((p) => `captain-${p.player_id}` === scenario.key);
  if (!chosen || !currentCaptain) return null;
  const changes = rivals
    .map((row) => scenario.delta[String(row.manager.entry_id)])
    .filter((change): change is number => change !== undefined);
  if (changes.length === 0) return null;

  const better = changes.filter((change) => change >= NOISE).length;
  const worse = changes.filter((change) => change <= -NOISE).length;
  return {
    newCaptain: chosen.name,
    oldCaptain: currentCaptain.name,
    // Captaincy doubles one score, so moving the armband changes the expected
    // total by exactly the difference between the two players' projections.
    points: chosen.projected_points - currentCaptain.projected_points,
    average: changes.reduce((sum, change) => sum + change, 0) / changes.length,
    better,
    worse,
    same: changes.length - better - worse,
  };
}

/** "▼ from 43.0%": the direction and where it started, with no jargon. */
function Change({ before, delta }: { before: number; delta: number }) {
  if (Math.abs(delta) < 0.0005) {
    return <span className="text-ink-faint">no change</span>;
  }
  const up = delta > 0;
  return (
    <span className={cx("num", up ? "text-you" : "text-rival")}>
      <span aria-hidden="true">{up ? "▲" : "▼"} </span>
      <span className="sr-only">{up ? "up" : "down"} </span>
      from {(before * 100).toFixed(1)}%
    </span>
  );
}

function PlayerRow({
  player,
  selected,
  isCurrent,
  onSelect,
}: {
  player: SquadPlayer;
  selected: boolean;
  isCurrent: boolean;
  onSelect: () => void;
}) {
  const doubtful = player.start_probability < 0.6 || player.status !== "a";
  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      // FPL only lets the armband go on a starter.
      disabled={!player.is_starter}
      title={player.is_starter ? undefined : "Only your starting eleven can be captain"}
      onClick={onSelect}
      className={cx(
        "flex w-full min-h-[44px] items-center gap-2 rounded-[8px] border px-3 py-2 text-left transition-colors",
        selected
          ? "border-you bg-[#0f1f19]"
          : "border-transparent enabled:hover:border-border-strong enabled:hover:bg-surface-2",
        !player.is_starter && "cursor-not-allowed opacity-60",
      )}
    >
      <span className="w-9 shrink-0 text-[11px] uppercase tracking-wider text-ink-faint">
        {player.position}
      </span>
      <span className="min-w-0 flex-1 truncate">
        <span className="text-ink">{player.name}</span>{" "}
        <span className="text-xs text-ink-faint">{player.team}</span>
        {doubtful ? (
          <span className="ml-1.5 text-xs text-warn" title={player.news ?? "Doubtful"}>
            ⚠
          </span>
        ) : null}
      </span>
      <span className="num shrink-0 text-sm text-ink-dim">
        {player.projected_points.toFixed(1)}
      </span>
      <span className="num hidden shrink-0 text-xs text-ink-faint sm:inline">
        {money(player.price)}
      </span>
      {selected ? (
        <Badge tone="you">{isCurrent ? "C" : "new C"}</Badge>
      ) : isCurrent ? (
        <span className="text-[11px] text-ink-faint">was C</span>
      ) : null}
    </button>
  );
}
