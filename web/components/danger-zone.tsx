"use client";

import { useState } from "react";

import { Button, Card } from "@/components/ui";
import { ApiError, clientFetch } from "@/lib/api";

/**
 * Deletion is self-serve and immediate. There is one confirmation step because
 * it is irreversible after 30 days — not to talk anybody out of it.
 */
export function DangerZone() {
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function remove() {
    setBusy(true);
    setError(null);
    try {
      await clientFetch("/me", {
        method: "DELETE",
        body: JSON.stringify({ confirm: true }),
      });
      setDone(true);
      window.setTimeout(() => {
        window.location.href = "/";
      }, 2500);
    } catch (err) {
      setBusy(false);
      setError(err instanceof ApiError ? err.message : "Could not delete the account.");
    }
  }

  if (done) {
    return (
      <Card className="p-6">
        <h2 className="font-semibold text-ink">Your account is closed</h2>
        <p className="mt-2 text-sm text-ink-dim">
          Access has ended. Everything we hold is permanently removed within 30 days.
          Taking you back to the homepage…
        </p>
      </Card>
    );
  }

  return (
    <Card className="border-rival-dim p-6">
      <h2 className="font-semibold text-rival">Delete your account</h2>
      <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-dim">
        Access ends immediately. Everything we hold about you — including any AI
        request logs — is permanently removed within 30 days. Download your data first
        if you want to keep it.
      </p>

      {!confirming ? (
        <Button variant="danger" onClick={() => setConfirming(true)} className="mt-4">
          Delete my account
        </Button>
      ) : (
        <div className="mt-4 flex flex-wrap gap-2">
          <Button variant="danger" onClick={remove} disabled={busy}>
            {busy ? "Deleting…" : "Yes, delete everything"}
          </Button>
          <Button variant="ghost" onClick={() => setConfirming(false)} disabled={busy}>
            Keep my account
          </Button>
        </div>
      )}

      {error ? (
        <p role="alert" className="mt-3 text-sm text-rival">
          {error}
        </p>
      ) : null}
    </Card>
  );
}
