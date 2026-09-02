"use client";

import { useState } from "react";

import { Button } from "@/components/ui";
import { ApiError, clientFetch, track } from "@/lib/api";

export function BillingActions({
  isPro,
  canPurchase,
}: {
  isPro: boolean;
  canPurchase: boolean;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function openPortal() {
    setBusy(true);
    setError(null);
    try {
      const { url } = await clientFetch<{ url: string }>("/billing/portal", {
        method: "POST",
      });
      window.location.href = url;
    } catch (err) {
      setBusy(false);
      setError(
        err instanceof ApiError ? err.message : "Could not open the billing portal.",
      );
    }
  }

  async function checkout(plan: "monthly" | "season") {
    setBusy(true);
    setError(null);
    track("checkout_started", { plan });
    try {
      const { url } = await clientFetch<{ url: string }>("/billing/checkout", {
        method: "POST",
        body: JSON.stringify({ plan }),
      });
      window.location.href = url;
    } catch (err) {
      setBusy(false);
      setError(err instanceof ApiError ? err.message : "Could not start checkout.");
    }
  }

  if (isPro) {
    return (
      <div className="text-right">
        <Button variant="secondary" onClick={openPortal} disabled={busy}>
          {busy ? "Opening…" : "Manage billing"}
        </Button>
        {error ? (
          <p role="alert" className="mt-1 max-w-[16rem] text-xs text-rival">
            {error}
          </p>
        ) : null}
      </div>
    );
  }

  if (!canPurchase) {
    return (
      <p className="max-w-[16rem] text-sm text-ink-faint">
        Pro is not available to under-16s. Everything on the free plan stays available
        to you.
      </p>
    );
  }

  return (
    <div className="text-right">
      <div className="flex flex-wrap justify-end gap-2">
        <Button variant="secondary" onClick={() => checkout("monthly")} disabled={busy}>
          €4.99 / month
        </Button>
        <Button onClick={() => checkout("season")} disabled={busy}>
          €29.99 / season
        </Button>
      </div>
      {error ? (
        <p role="alert" className="mt-1 max-w-[18rem] text-xs text-rival">
          {error}
        </p>
      ) : null}
    </div>
  );
}
