"use client";

import { useRouter } from "next/navigation";
import { useId, useState } from "react";

import { Button, Card } from "@/components/ui";
import type { LeagueBoardRow } from "@/lib/types";

/**
 * Without knowing which manager the visitor is, the odds column is meaningless.
 * Asking them to pick their own name from the league is far easier than asking
 * for a manager ID they have never heard of.
 */
export function EntryPicker({
  leagueId,
  rows,
}: {
  leagueId: number;
  rows: LeagueBoardRow[];
}) {
  const router = useRouter();
  const selectId = useId();
  const [entry, setEntry] = useState("");

  return (
    <Card className="p-5">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (entry) router.push(`/l/${leagueId}?entry=${entry}`);
        }}
        className="flex flex-col gap-3 sm:flex-row sm:items-end"
      >
        <div className="flex-1">
          <label htmlFor={selectId} className="block text-sm font-medium text-ink">
            Which one are you?
          </label>
          <p className="mt-1 text-sm text-ink-dim">
            We need this to work out your odds against everyone else.
          </p>
          <select
            id={selectId}
            value={entry}
            onChange={(event) => setEntry(event.target.value)}
            className="mt-3 min-h-[48px] w-full rounded-[8px] border border-border-strong bg-surface px-3 py-2.5 text-base text-ink focus:border-you focus:outline-none"
          >
            <option value="">Pick your name…</option>
            {rows.map((row) => (
              <option key={row.manager.entry_id} value={row.manager.entry_id}>
                {row.manager.player_name} — {row.manager.team_name}
              </option>
            ))}
          </select>
        </div>
        <Button type="submit" disabled={!entry} className="sm:mb-0">
          Show my odds
        </Button>
      </form>
    </Card>
  );
}
