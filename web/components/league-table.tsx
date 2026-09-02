import Link from "next/link";

import { Card, cx } from "@/components/ui";
import { ordinal, signedInt } from "@/lib/format";
import type { LeagueBoard } from "@/lib/types";

/**
 * The board. `P(you finish above)` is the entire reason this page exists, so it
 * is the column that survives on a phone.
 *
 * A real `<table>` with scope attributes, not a grid of divs — a screen reader
 * has to be able to read "Dan, 44 points behind, 18 percent" as a row.
 */
export function LeagueTable({ board }: { board: LeagueBoard }) {
  const hasYou = board.you !== null;

  return (
    <>
      {/* Desktop: the full table. */}
      <Card className="hidden overflow-hidden md:block">
        <div className="scroll-x">
          <table className="w-full border-collapse text-sm">
            <caption className="sr-only">
              {board.league.name} standings with your probability of finishing above
              each manager
            </caption>
            <thead>
              <tr className="border-b border-border text-left text-[11px] uppercase tracking-wider text-ink-faint">
                <th scope="col" className="px-4 py-3 font-semibold">
                  #
                </th>
                <th scope="col" className="px-4 py-3 font-semibold">
                  Manager
                </th>
                <th scope="col" className="px-4 py-3 font-semibold">
                  Team
                </th>
                <th scope="col" className="px-4 py-3 text-right font-semibold">
                  Points
                </th>
                {hasYou ? (
                  <>
                    <th scope="col" className="px-4 py-3 text-right font-semibold">
                      Gap
                    </th>
                    <th scope="col" className="px-4 py-3 text-right font-semibold">
                      P(you above)
                    </th>
                  </>
                ) : null}
                <th scope="col" className="px-4 py-3 text-right font-semibold">
                  P(wins)
                </th>
                <th scope="col" className="px-4 py-3 text-right font-semibold">
                  Trend
                </th>
              </tr>
            </thead>
            <tbody>
              {board.rows.map((row, index) => {
                const odds = row.odds_vs_you;
                return (
                  <tr
                    key={row.manager.entry_id}
                    className={cx(
                      "border-b border-border/60 last:border-0",
                      row.is_you && "bg-[#0f1f19]",
                    )}
                  >
                    <td className="num px-4 py-3 text-ink-faint">{index + 1}</td>
                    <th
                      scope="row"
                      className={cx(
                        "px-4 py-3 text-left font-medium",
                        row.is_you ? "text-you" : "text-ink",
                      )}
                    >
                      {row.manager.player_name}
                      {row.is_you ? (
                        <span className="ml-2 text-[11px] font-normal uppercase tracking-wider text-you">
                          you
                        </span>
                      ) : null}
                    </th>
                    <td className="px-4 py-3 text-ink-dim">{row.manager.team_name}</td>
                    <td className="num px-4 py-3 text-right">{row.manager.total}</td>
                    {hasYou ? (
                      <>
                        <td className="num px-4 py-3 text-right text-ink-dim">
                          {row.is_you ? "—" : odds ? signedInt(odds.gap_now) : "—"}
                        </td>
                        <td className="num px-4 py-3 text-right">
                          {row.is_you ? (
                            "—"
                          ) : odds ? (
                            <Link
                              href={`/l/${board.league.id}/vs/${row.manager.entry_id}?you=${board.you}`}
                              className={cx(
                                "font-semibold underline-offset-4 hover:underline",
                                odds.p_above >= 0.6
                                  ? "text-you"
                                  : odds.p_above <= 0.25
                                    ? "text-rival"
                                    : "text-ink",
                              )}
                            >
                              {Math.round(odds.p_above * 100)}%
                            </Link>
                          ) : (
                            "—"
                          )}
                        </td>
                      </>
                    ) : null}
                    <td className="num px-4 py-3 text-right text-ink-dim">
                      {Math.round(row.p_win * 100)}%
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Trend
                        rank={row.manager.rank}
                        lastRank={row.manager.last_rank}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Mobile: a card list. P(above) stays visible in every card. */}
      <ul className="space-y-2 md:hidden">
        {board.rows.map((row, index) => {
          const odds = row.odds_vs_you;
          const inner = (
            <>
              <div className="flex items-baseline gap-2">
                <span className="num text-sm text-ink-faint">{index + 1}</span>
                <span
                  className={cx(
                    "truncate font-medium",
                    row.is_you ? "text-you" : "text-ink",
                  )}
                >
                  {row.manager.player_name}
                </span>
                {row.is_you ? (
                  <span className="text-[10px] uppercase tracking-wider text-you">
                    you
                  </span>
                ) : null}
              </div>
              <div className="mt-0.5 truncate text-sm text-ink-dim">
                {row.manager.team_name}
              </div>
              <div className="num mt-1 text-xs text-ink-faint">
                {row.manager.total} pts
                {odds && !row.is_you ? ` · ${signedInt(odds.gap_now)} gap` : ""}
              </div>
            </>
          );

          return (
            <li key={row.manager.entry_id}>
              <Card
                className={cx(
                  "flex items-center gap-4 p-4",
                  row.is_you && "border-you-dim bg-[#0f1f19]",
                )}
              >
                {odds && !row.is_you ? (
                  <Link
                    href={`/l/${board.league.id}/vs/${row.manager.entry_id}?you=${board.you}`}
                    className="flex min-w-0 flex-1 flex-col"
                  >
                    {inner}
                  </Link>
                ) : (
                  <div className="min-w-0 flex-1">{inner}</div>
                )}
                <div className="shrink-0 text-right">
                  {row.is_you ? (
                    <span className="num text-sm text-ink-faint">—</span>
                  ) : odds ? (
                    <>
                      <div
                        className={cx(
                          "num text-2xl font-semibold",
                          odds.p_above >= 0.6
                            ? "text-you"
                            : odds.p_above <= 0.25
                              ? "text-rival"
                              : "text-ink",
                        )}
                      >
                        {Math.round(odds.p_above * 100)}%
                      </div>
                      <div className="text-[10px] uppercase tracking-wider text-ink-faint">
                        you above
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="num text-xl text-ink-dim">
                        {Math.round(row.p_win * 100)}%
                      </div>
                      <div className="text-[10px] uppercase tracking-wider text-ink-faint">
                        to win
                      </div>
                    </>
                  )}
                </div>
              </Card>
            </li>
          );
        })}
      </ul>
    </>
  );
}

/** Movement always carries an arrow and a word, never colour alone. */
function Trend({ rank, lastRank }: { rank: number | null; lastRank: number | null }) {
  if (rank === null || lastRank === null || rank === lastRank) {
    return (
      <span className="text-ink-faint">
        <span aria-hidden="true">–</span>
        <span className="sr-only">no change</span>
      </span>
    );
  }
  const up = rank < lastRank;
  const places = Math.abs(rank - lastRank);
  return (
    <span className={up ? "text-you" : "text-rival"}>
      <span aria-hidden="true">{up ? "▲" : "▼"}</span>
      <span className="num ml-1">{places}</span>
      <span className="sr-only">
        {up ? "up" : "down"} {places} place{places === 1 ? "" : "s"} from{" "}
        {ordinal(lastRank)}
      </span>
    </span>
  );
}
