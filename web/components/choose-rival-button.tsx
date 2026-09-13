"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { Button } from "@/components/ui";
import { ApiError, clientFetch } from "@/lib/api";

/**
 * The free plan's one rival is chosen on purpose, here, rather than spent on
 * whichever dossier happens to be opened first.
 */
export function ChooseRivalButton({
  leagueId,
  entryId,
  rivalName,
}: {
  leagueId: number;
  entryId: number;
  rivalName: string;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [refreshing, startRefresh] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const working = busy || refreshing;

  async function choose() {
    setBusy(true);
    setError(null);
    try {
      await clientFetch(`/leagues/${leagueId}/rivals/${entryId}/free-dossier`, {
        method: "POST",
      });
      startRefresh(() => router.refresh());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "That did not work. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <Button onClick={choose} disabled={working}>
        {working ? "Unlocking…" : `Make ${rivalName} my free rival`}
      </Button>
      {error ? (
        <p role="alert" className="mt-2 text-sm text-rival">
          {error}
        </p>
      ) : null}
    </div>
  );
}
