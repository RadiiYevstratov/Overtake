"use client";

import { useRouter } from "next/navigation";
import { useId, useState, useTransition } from "react";

import { Button, Card } from "@/components/ui";
import type { LeagueBoardRow } from "@/lib/types";

/**
 * The cards above are the rivals the maths says matter. Everyone also has the
 * rival they personally care about — a brother-in-law sitting in 14th — and
 * that comparison should be one pick away, not a hunt through the table.
 */
export function RivalPicker({
  leagueId,
  you,
  rows,
}: {
  leagueId: number;
  you: number;
  rows: LeagueBoardRow[];
}) {
  const router = useRouter();
  const selectId = useId();
  const [entry, setEntry] = useState("");
  const [opening, startOpening] = useTransition();

  if (rows.length === 0) return null;

  return (
    <Card className="mt-4 p-5">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (!entry) return;
          startOpening(() => router.push(`/l/${leagueId}/vs/${entry}?you=${you}`));
        }}
        className="flex flex-col gap-3 sm:flex-row sm:items-end"
      >
        <div className="flex-1">
          <label htmlFor={selectId} className="block text-sm font-medium text-ink">
            Compare with anyone in the league
          </label>
          <select
            id={selectId}
            value={entry}
            onChange={(event) => setEntry(event.target.value)}
            className="mt-3 min-h-[48px] w-full rounded-[8px] border border-border-strong bg-surface px-3 py-2.5 text-[1rem] text-ink focus:border-you focus:outline-none"
          >
            <option value="">Pick a manager…</option>
            {rows.map((row) => (
              <option key={row.manager.entry_id} value={row.manager.entry_id}>
                {row.manager.rank ? `${row.manager.rank}. ` : ""}
                {row.manager.player_name} — {row.manager.team_name}
                {row.odds_vs_you
                  ? ` · you ${Math.round(row.odds_vs_you.p_above * 100)}% to finish above`
                  : ""}
              </option>
            ))}
          </select>
        </div>
        <Button type="submit" disabled={!entry || opening}>
          {opening ? "Opening…" : "Compare"}
        </Button>
      </form>
    </Card>
  );
}
