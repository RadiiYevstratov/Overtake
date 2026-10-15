"use client";

import Link from "next/link";
import { useState } from "react";

import { Button, Card } from "@/components/ui";
import { ApiError, clientFetch, track } from "@/lib/api";

type PaidPlan = "monthly" | "season";

interface Viewer {
  isPro: boolean;
  signedIn: boolean;
  canPurchase: boolean;
}

const PRIMARY_LINK =
  "inline-flex min-h-[44px] w-full items-center justify-center rounded-[8px] bg-you px-4 py-2.5 text-sm font-semibold text-[#06231a] transition-colors hover:bg-[#4ae8a5]";
const SECONDARY_LINK =
  "inline-flex min-h-[44px] w-full items-center justify-center rounded-[8px] border border-border-strong px-4 py-2.5 text-sm transition-colors hover:border-ink-faint";

/**
 * The action at the foot of a plan card — the one that actually applies to
 * the person reading it. Pro is bought from an account (the subscription,
 * refunds and the age rule all hang off it), so a signed-out visitor is sent
 * to create one and comes straight back here; a signed-in one goes to Stripe.
 */
export function PlanAction({ plan, isPro, signedIn, canPurchase }: Viewer & { plan: PaidPlan }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function checkout() {
    setBusy(true);
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
      setBusy(false);
      setError(err instanceof ApiError ? err.message : "Could not start checkout.");
    }
  }

  if (isPro) {
    return (
      <Link href="/app/account" className={SECONDARY_LINK}>
        Manage your plan
      </Link>
    );
  }
  if (!signedIn) {
    return (
      <Link href="/signin?next=/pricing" className={PRIMARY_LINK}>
        Create a free account to buy
      </Link>
    );
  }
  if (!canPurchase) {
    return <p className="text-center text-sm text-ink-faint">Not available under 16</p>;
  }
  return (
    <>
      <Button
        variant={plan === "season" ? "primary" : "secondary"}
        onClick={checkout}
        disabled={busy}
        className="w-full"
      >
        {busy
          ? "Opening checkout…"
          : plan === "season"
            ? "Buy the season pass — €29.99"
            : "Go Pro — €4.99 a month"}
      </Button>
      {error ? (
        <p role="alert" className="mt-2 text-center text-sm text-rival">
          {error}
        </p>
      ) : null}
    </>
  );
}

/** The free card's action: start using it, or say it is what you have. */
export function FreePlanAction({ isPro, signedIn }: Viewer) {
  if (signedIn) {
    return (
      <p className="text-center text-sm text-ink-faint">
        {isPro ? "Included in Pro" : "Your current plan"}
      </p>
    );
  }
  return (
    <Link href="/" className={SECONDARY_LINK}>
      Start free — paste your league ID
    </Link>
  );
}

/** What is true for this reader about buying, under the cards. */
export function PricingActions({ isPro, signedIn, canPurchase }: Viewer) {
  if (isPro) {
    return (
      <Card className="p-5 text-center">
        <p className="text-ink">You already have Pro. Everything on this page is unlocked.</p>
      </Card>
    );
  }

  if (!signedIn) {
    return (
      <Card className="p-5 text-center">
        <p className="text-ink-dim">
          Pro is bought from a free account: sign in with your email — no password — and
          you come straight back here to choose monthly or the season pass.
        </p>
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
    <p className="text-center text-sm text-ink-faint">
      Card handled entirely by Stripe. We never see your card details.
    </p>
  );
}
