import Link from "next/link";

import { Card } from "@/components/ui";
import { ViewTracker } from "@/components/view-tracker";
import { serverFetchOrNull } from "@/lib/api";
import type { Me } from "@/lib/types";

/**
 * Where checkout lands. Never a generic "welcome" — the user was blocked on
 * something specific, so this page points straight back at it.
 */
export default async function WelcomePage() {
  const me = (await serverFetchOrNull<Me>("/me"))!;

  return (
    <div className="mx-auto max-w-xl py-8">
      <ViewTracker event="checkout_completed" props={{ plan: me.plan.source }} />
      <Card className="border-you-dim p-8 text-center">
        <h1 className="text-3xl font-bold tracking-tight text-you">
          {me.plan.is_pro ? "You're in." : "Almost there"}
        </h1>
        {me.plan.is_pro ? (
          <>
            <p className="mt-3 leading-relaxed text-ink-dim">
              Every rival, every league, the Deadline Brief before every deadline, and
              the simulator. Nothing else changes about how you use Overtake.
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-3">
              <Link
                href="/app/brief"
                className="inline-flex min-h-[44px] items-center rounded-[8px] bg-you px-5 py-2.5 text-sm font-semibold text-[#06231a] transition-colors hover:bg-[#4ae8a5]"
              >
                Read your first brief
              </Link>
              <Link
                href="/app"
                className="inline-flex min-h-[44px] items-center rounded-[8px] border border-border-strong px-5 py-2.5 text-sm transition-colors hover:border-ink-faint"
              >
                Back to your league
              </Link>
            </div>
          </>
        ) : (
          <p className="mt-3 leading-relaxed text-ink-dim">
            Stripe is still confirming the payment. This usually takes a few seconds —
            refresh in a moment and Pro will be live. Nothing has gone wrong.
          </p>
        )}
      </Card>
      <p className="mt-6 text-center text-sm text-ink-faint">
        Changed your mind? Full refund on request within 14 days, no questions asked.
      </p>
    </div>
  );
}
