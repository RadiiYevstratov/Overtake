"use client";

import Link from "next/link";
import { useState } from "react";

import { Button, Card } from "@/components/ui";
import { ApiError, clientFetch, track } from "@/lib/api";

export function PricingActions({
  isPro,
  signedIn,
  canPurchase,
}: {
  isPro: boolean;
  signedIn: boolean;
  canPurchase: boolean;
}) {
  const [busy, setBusy] = useState<"monthly" | "season" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function checkout(plan: "monthly" | "season") {
    setBusy(plan);
    setError(null);
    track("plan_selected", { plan });
    track("checkout_started", { plan });
    try {
      const { url } = await clientFetch<{ url: string }>("/billing/checkout", {
        method: "POST",
        body: JSON.stringify({ plan }),
      });
      window.location.href = url;
    } catch (err) {
      setBusy(null);
      setError(err instanceof ApiError ? err.message : "Could not start checkout.");
    }
  }

  if (isPro) {
    return (
      <Card className="p-5 text-center">
        <p className="text-ink">
          You already have Pro. Everything on this page is unlocked.
        </p>
        <Link
          href="/app/account"
          className="mt-3 inline-flex min-h-[44px] items-center rounded-[8px] border border-border-strong px-4 py-2.5 text-sm transition-colors hover:border-ink-faint"
        >
          Manage your plan
        </Link>
      </Card>
    );
  }

  if (!signedIn) {
    return (
      <Card className="p-5 text-center">
        <p className="text-ink-dim">
          Create a free account first — you can upgrade any time from your account page.
        </p>
        <Link
          href="/signin?next=/pricing"
          className="mt-3 inline-flex min-h-[44px] items-center rounded-[8px] bg-you px-5 py-2.5 text-sm font-semibold text-[#06231a] transition-colors hover:bg-[#4ae8a5]"
        >
          Create a free account
        </Link>
      </Card>
    );
  }

  if (!canPurchase) {
    return (
      <Card className="p-5 text-center text-ink-dim">
        Overtake Pro is not available to under-16s. Everything on the free plan stays
        available to you, permanently.
      </Card>
    );
  }

  return (
    <Card className="p-5">
      <div className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
        <Button
          variant="secondary"
          onClick={() => checkout("monthly")}
          disabled={busy !== null}
          className="w-full sm:w-auto"
        >
          {busy === "monthly" ? "Opening checkout…" : "Go Pro — €4.99 a month"}
        </Button>
        <Button
          onClick={() => checkout("season")}
          disabled={busy !== null}
          className="w-full sm:w-auto"
        >
          {busy === "season" ? "Opening checkout…" : "Season pass — €29.99"}
        </Button>
      </div>
      <p className="mt-3 text-center text-sm text-ink-faint">
        Card handled entirely by Stripe. We never see your card details.
      </p>
      {error ? (
        <p role="alert" className="mt-3 text-center text-sm text-rival">
          {error}
        </p>
      ) : null}
    </Card>
  );
}
