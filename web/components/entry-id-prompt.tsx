"use client";

import { useRouter } from "next/navigation";
import { useId, useState } from "react";

import { Button, Card } from "@/components/ui";
import { ApiError, clientFetch } from "@/lib/api";
import type { LeagueBoardRow } from "@/lib/types";

/**
 * Without a manager ID we cannot say "you vs Dan", which is the whole product.
 * Asking the user to pick their own name out of the league is far easier than
 * asking for an ID they have never seen.
 */
export function EntryIdPrompt({ rows }: { rows: LeagueBoardRow[] }) {
  const router = useRouter();
  const selectId = useId();
  const [entry, setEntry] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (!entry) return;
    setSaving(true);
    setError(null);
    try {
      await clientFetch("/me", {
        method: "PATCH",
        body: JSON.stringify({ fpl_entry_id: Number.parseInt(entry, 10) }),
      });
      router.refresh();
    } catch (err) {
      setSaving(false);
      setError(err instanceof ApiError ? err.message : "Could not save that.");
    }
  }

  return (
    <Card className="border-you-dim p-5">
      <form onSubmit={save} className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <div className="flex-1">
          <label htmlFor={selectId} className="block font-medium">
            Which manager are you?
          </label>
          <p className="mt-1 text-sm text-ink-dim">
            We need this to compare your squad against everyone else&apos;s.
          </p>
          <select
            id={selectId}
            value={entry}
            onChange={(event) => setEntry(event.target.value)}
            className="mt-3 min-h-[48px] w-full rounded-[8px] border border-border-strong bg-base px-3 py-2.5 text-base focus:border-you focus:outline-none"
          >
            <option value="">Pick your name…</option>
            {rows.map((row) => (
              <option key={row.manager.entry_id} value={row.manager.entry_id}>
                {row.manager.player_name} — {row.manager.team_name}
              </option>
            ))}
          </select>
        </div>
        <Button type="submit" disabled={!entry || saving}>
          {saving ? "Saving…" : "That's me"}
        </Button>
      </form>
      {error ? (
        <p role="alert" className="mt-2 text-sm text-rival">
          {error}
        </p>
      ) : null}
    </Card>
  );
}
