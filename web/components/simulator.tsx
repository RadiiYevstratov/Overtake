"use client";

import { useEffect, useState } from "react";

import { Badge, Button, Card, Delta, RuleHeading, Skeleton, cx } from "@/components/ui";
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
  scenariosPerGameweek,
}: {
  leagueId: number;
  board: LeagueBoard;
  scenariosPerGameweek: number;
}) {
  const [squad, setSquad] = useState<Squad | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [captain, setCaptain] = useState<number | null>(null);
  const [result, setResult] = useState<ScenarioResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runs, setRuns] = useState(0);

  useEffect(() => {
    let cancelled = false;
    clientFetch<Squad>(`/leagues/${leagueId}/squad`)
      .then((data) => {
        if (cancelled) return;
        setSquad(data);
        setCaptain(data.players.find((p) => p.is_captain)?.player_id ?? null);
      })
      .catch((err) => {
        if (!cancelled) {
          setLoadError(
            err instanceof ApiError ? err.message : "We could not load your squad.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [leagueId]);

  const currentCaptain = squad?.players.find((p) => p.is_captain) ?? null;
  const changed = captain !== null && captain !== currentCaptain?.player_id;
  const remaining = Math.max(0, scenariosPerGameweek - runs);

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
      setRuns((n) => n + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "That scenario could not run.");
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

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,24rem)_1fr]">
      {/* ------------------------------------------------------- squad */}
      <Card className="h-fit p-5">
        <RuleHeading>Your squad</RuleHeading>

        {loadError ? (
          <p role="alert" className="text-sm text-rival">
            {loadError}
          </p>
        ) : !squad ? (
          <div className="space-y-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-11 w-full" />
            ))}
          </div>
        ) : (
          <>
            <p className="mb-3 text-sm text-ink-dim">
              Tap a player to captain them. The doubled score is the biggest single
              lever you have this week.
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
              <Button onClick={run} disabled={!changed || busy || remaining === 0} className="flex-1">
                {busy ? "Simulating…" : "Run this scenario"}
              </Button>
              {result ? (
                <Button variant="secondary" onClick={reset}>
                  Reset
                </Button>
              ) : null}
            </div>

            <p className="mt-3 text-xs text-ink-faint">
              <span className="num">{remaining}</span> scenarios left this gameweek
              {!changed && !result ? " · pick a different captain to run one" : ""}
            </p>

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

                  <div className="w-20 shrink-0 text-right sm:w-24">
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
                      {Math.round(shown * 100)}%
                    </div>
                    {delta !== undefined ? (
                      <div className="mt-0.5 text-xs">
                        <Delta value={delta} />
                      </div>
                    ) : null}
                  </div>
                </Card>
              </li>
            );
          })}
        </ul>

        <p className="mt-4 text-sm leading-relaxed text-ink-faint">
          Every scenario is scored against the same 20,000 simulated seasons as the
          baseline, so a change of half a percentage point is a real difference and not
          sampling noise.
        </p>
      </div>
    </div>
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
      onClick={onSelect}
      className={cx(
        "flex w-full min-h-[44px] items-center gap-2 rounded-[8px] border px-3 py-2 text-left transition-colors",
        selected
          ? "border-you bg-[#0f1f19]"
          : "border-transparent hover:border-border-strong hover:bg-surface-2",
        !player.is_starter && "opacity-60",
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
