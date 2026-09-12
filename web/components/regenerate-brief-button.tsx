"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { Button } from "@/components/ui";
import { ApiError, clientFetch } from "@/lib/api";

export function RegenerateBriefButton({
  leagueId,
  used,
  allowed,
  canRegenerate,
}: {
  leagueId: number;
  used: number;
  allowed: number;
  canRegenerate: boolean;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  // The new brief is not on screen until the page has re-rendered with it, so
  // the button keeps saying "Rewriting…" until then instead of flipping back.
  const [refreshing, startRefresh] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const remaining = Math.max(0, allowed - used);
  const working = busy || refreshing;

  async function regenerate() {
    setBusy(true);
    setError(null);
    try {
      await clientFetch(`/leagues/${leagueId}/brief/regenerate`, { method: "POST" });
      startRefresh(() => router.refresh());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not rewrite the brief.");
    } finally {
      setBusy(false);
    }
  }

  // Without an AI writer a rewrite would come back word for word the same.
  if (!canRegenerate) return null;

  return (
    <div className="text-right">
      <Button
        variant="secondary"
        onClick={regenerate}
        disabled={working || remaining === 0}
        title={
          remaining === 0
            ? "You have used this gameweek's rewrites"
            : `${remaining} left this gameweek`
        }
      >
        {working ? "Rewriting…" : "Rewrite"}
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
