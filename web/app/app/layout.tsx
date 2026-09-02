import Link from "next/link";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { AppNav } from "@/components/app-nav";
import { serverFetchOrNull } from "@/lib/api";
import type { Me } from "@/lib/types";

export const metadata = { robots: { index: false, follow: false } };

export default async function AppLayout({ children }: { children: ReactNode }) {
  const me = await serverFetchOrNull<Me>("/me");
  if (!me) redirect("/signin?next=/app");

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
      {me.plan.in_grace_period ? <PastDueBanner /> : null}
      {me.plan.cancel_at_period_end && me.plan.current_period_end ? (
        <CancelledNotice until={me.plan.current_period_end} />
      ) : null}
      <AppNav isPro={me.plan.is_pro} />
      <div className="mt-8">{children}</div>
    </div>
  );
}

/**
 * A failed payment keeps full access for seven days with a dismissible banner,
 * then downgrades. Data is never deleted. No guilt copy.
 */
function PastDueBanner() {
  return (
    <div
      role="status"
      className="mb-6 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-[8px] border border-[#5a4a15] bg-[#1e1a0c] px-4 py-3 text-sm text-warn"
    >
      <span>
        Your last payment did not go through. You keep everything for now — updating
        your card fixes it.
      </span>
      <Link href="/app/account" className="underline hover:text-ink">
        Update payment method
      </Link>
    </div>
  );
}

function CancelledNotice({ until }: { until: string }) {
  const date = new Date(until).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
  });
  return (
    <div
      role="status"
      className="mb-6 rounded-[8px] border border-border bg-surface px-4 py-3 text-sm text-ink-dim"
    >
      Pro until <span className="num text-ink">{date}</span>. Nothing changes until
      then.
    </div>
  );
}
