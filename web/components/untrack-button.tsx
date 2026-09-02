"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui";
import { ApiError, clientFetch } from "@/lib/api";

export function UntrackButton({ leagueId }: { leagueId: number }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function untrack() {
    setBusy(true);
    setError(null);
    try {
      await clientFetch(`/leagues/${leagueId}/track`, { method: "DELETE" });
      router.refresh();
    } catch (err) {
      setBusy(false);
      setError(err instanceof ApiError ? err.message : "Could not remove that league.");
    }
  }

  return (
    <div className="text-right">
      <Button variant="ghost" onClick={untrack} disabled={busy}>
        {busy ? "Removing…" : "Stop tracking"}
      </Button>
      {error ? (
        <p role="alert" className="text-xs text-rival">
          {error}
        </p>
      ) : null}
    </div>
  );
}
