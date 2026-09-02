"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui";
import { ApiError, clientFetch } from "@/lib/api";

export function RegenerateBriefButton({
  leagueId,
  used,
  allowed,
}: {
  leagueId: number;
  used: number;
  allowed: number;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const remaining = Math.max(0, allowed - used);

  async function regenerate() {
    setBusy(true);
    setError(null);
    try {
      await clientFetch(`/leagues/${leagueId}/brief/regenerate`, { method: "POST" });
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not regenerate.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="text-right">
      <Button
        variant="secondary"
        onClick={regenerate}
        disabled={busy || remaining === 0}
        title={
          remaining === 0
            ? "You have used this gameweek's regenerations"
            : `${remaining} left this gameweek`
        }
      >
        {busy ? "Rewriting…" : "Rewrite"}
      </Button>
      <p className="mt-1 text-[11px] text-ink-faint">
        <span className="num">{remaining}</span> left this GW
      </p>
      {error ? (
        <p role="alert" className="mt-1 max-w-[14rem] text-xs text-rival">
          {error}
        </p>
      ) : null}
    </div>
  );
}
