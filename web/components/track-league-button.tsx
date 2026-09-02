"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui";
import { ApiError, clientFetch } from "@/lib/api";

export function TrackLeagueButton({ leagueId }: { leagueId: number }) {
  const router = useRouter();
  const [state, setState] = useState<"idle" | "saving" | "saved">("idle");
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setState("saving");
    setError(null);
    try {
      await clientFetch(`/leagues/${leagueId}/track`, { method: "POST" });
      setState("saved");
      router.refresh();
    } catch (err) {
      setState("idle");
      setError(
        err instanceof ApiError ? err.message : "Could not save that league.",
      );
    }
  }

  return (
    <div className="text-right">
      <Button
        variant="secondary"
        onClick={save}
        disabled={state !== "idle"}
        aria-live="polite"
      >
        {state === "saved" ? "Saved ✓" : state === "saving" ? "Saving…" : "Save league"}
      </Button>
      {error ? (
        <p role="alert" className="mt-1 max-w-[16rem] text-xs text-rival">
          {error}
        </p>
      ) : null}
    </div>
  );
}
