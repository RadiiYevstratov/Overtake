import Link from "next/link";

import { serverFetchOptional } from "@/lib/api";
import { serverFetchPublic } from "@/lib/public-api";
import type { LaunchOffer } from "@/lib/types";

/**
 * The launch offer, at the top of the page.
 *
 * The count comes from Stripe, not from a constant: when the thirtieth person
 * has taken it, the banner stops appearing rather than promising a code the
 * checkout would refuse. It states the price after the free month too — the
 * card is taken at sign-up, and saying so here is the same anti-dark-pattern
 * promise the pricing page makes.
 */
export async function FounderOffer({
  action = { href: "/pricing", label: "See the plans" },
}: {
  /** Where the banner leads. On the pricing page itself, the next step instead. */
  action?: { href: string; label: string };
} = {}) {
  // Ten minutes, and deliberately not shorter: this fetch decides how often
  // the whole page re-renders, and a page that re-renders every minute keeps
  // the database awake around the clock for the sake of a counter that moves
  // thirty times in total.
  const offer = await serverFetchOptional(() =>
    serverFetchPublic<LaunchOffer>("/billing/offer", { revalidate: 600 }),
  );
  if (!offer?.active || !offer.code) return null;

  const left =
    typeof offer.remaining === "number" && typeof offer.total === "number"
      ? `${offer.remaining} of ${offer.total} left`
      : null;

  return (
    <aside
      aria-label="Launch offer"
      className="border-b border-you/25 bg-you/[0.08]"
    >
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-center gap-x-3 gap-y-1 px-4 py-2.5 text-center text-sm sm:px-6">
        <span className="font-semibold text-ink">First month free</span>
        <span className="text-ink-dim">
          for the first {offer.total ?? 30} people — use code{" "}
          <span className="num rounded-[4px] bg-surface px-1.5 py-0.5 font-semibold tracking-wide text-you">
            {offer.code}
          </span>{" "}
          at checkout
          {left ? <span className="text-ink-faint"> · {left}</span> : null}
          <span className="text-ink-faint">
            {" "}
            · then €4.99 a month, cancel any time
          </span>
        </span>
        <Link href={action.href} className="underline underline-offset-2 hover:text-ink">
          {action.label}
        </Link>
      </div>
    </aside>
  );
}
