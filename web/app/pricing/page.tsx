import type { Metadata } from "next";
import Link from "next/link";

import { PricingActions } from "@/components/pricing-actions";
import { Card, RuleHeading } from "@/components/ui";
import { ViewTracker } from "@/components/view-tracker";
import { serverFetchOrNull } from "@/lib/api";
import type { Me } from "@/lib/types";

export const metadata: Metadata = {
  title: "Pricing",
  description:
    "Free forever for one league and one rival dossier a season. Pro is €4.99 a month or €29.99 for the whole season.",
  alternates: { canonical: "/pricing" },
};

export default async function PricingPage() {
  const me = await serverFetchOrNull<Me>("/me");

  return (
    <div className="mx-auto max-w-5xl px-4 py-14 sm:px-6">
      <ViewTracker event="paywall_shown" props={{ page: "pricing" }} />

      <h1 className="text-4xl font-bold tracking-tight">Pricing</h1>
      <p className="mt-3 max-w-2xl text-lg text-ink-dim">
        The free plan is permanently useful, not a trial. It gives you the whole league
        board and one full rival dossier every season.
      </p>

      <div className="mt-10 grid gap-4 md:grid-cols-3">
        <Plan
          name="Free"
          price="€0"
          cadence="forever"
          blurb="Enough to know whether the maths is worth anything to you."
          features={[
            "One league",
            "The full league board with win probabilities",
            "One rival dossier a season",
            "Shareable league card",
            "Every public player and gameweek page",
          ]}
        />
        <Plan
          name="Pro monthly"
          price="€4.99"
          cadence="a month"
          blurb="Cancel in one click, keep access to the end of the period."
          features={[
            "Every rival, in every league you are in",
            "Deadline Brief in-app and by email",
            "The Overtake Simulator",
            "Chip planner",
            "Ask-the-Gaffer",
          ]}
        />
        <Plan
          name="Season pass"
          price="€29.99"
          cadence="August to May"
          highlight
          blurb="One payment. No auto-renew, and no renewal decision in February."
          features={[
            "Everything in Pro monthly",
            "One payment, no subscription",
            "Nothing to cancel",
            "Cheaper than one bad −8 hit",
          ]}
        />
      </div>

      <div className="mt-8">
        <PricingActions
          isPro={me?.plan.is_pro ?? false}
          signedIn={Boolean(me)}
          canPurchase={!me || me.user.age_band !== "13_15"}
        />
      </div>

      <section className="mt-16">
        <RuleHeading>What we will not do</RuleHeading>
        <ul className="grid gap-4 sm:grid-cols-2">
          {[
            ["No pre-ticked upsells.", "Nothing is added to your basket by us."],
            ["No hidden auto-renew.", "The season pass simply ends. We email you in July."],
            [
              "No cancellation gauntlet.",
              "One click in the billing portal. No questions, no offers, no guilt.",
            ],
            [
              "No dark patterns on your data.",
              "Export or delete everything from your account page, without emailing anyone.",
            ],
          ].map(([title, body]) => (
            <li key={title}>
              <Card className="h-full p-5">
                <h3 className="font-semibold text-ink">{title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-ink-dim">{body}</p>
              </Card>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-14">
        <RuleHeading>Refunds</RuleHeading>
        <p className="max-w-2xl leading-relaxed text-ink-dim">
          EU and UK distance-selling rules give you a 14-day right to withdraw from a
          digital service. Some sellers ask you to waive it at checkout. We do not ask,
          and we honour it: email{" "}
          <a className="underline hover:text-ink" href="mailto:hello@overtake.app">
            hello@overtake.app
          </a>{" "}
          within 14 days and you get a full refund, no questions.
        </p>
      </section>

      <section className="mt-14">
        <RuleHeading>Who we do not sell to</RuleHeading>
        <p className="max-w-2xl leading-relaxed text-ink-dim">
          Overtake Pro is not available to under-16s, deliberately. Everything on the
          free plan is, and always will be. You can read more about how we handle age
          in the{" "}
          <Link href="/privacy" className="underline hover:text-ink">
            privacy policy
          </Link>
          .
        </p>
      </section>
    </div>
  );
}

function Plan({
  name,
  price,
  cadence,
  blurb,
  features,
  highlight,
}: {
  name: string;
  price: string;
  cadence: string;
  blurb: string;
  features: string[];
  highlight?: boolean;
}) {
  return (
    <Card className={`flex h-full flex-col p-6 ${highlight ? "border-you-dim" : ""}`}>
      {highlight ? (
        <span className="mb-3 inline-flex w-fit rounded-full border border-you-dim px-2.5 py-1 text-[11px] font-medium text-you">
          The natural unit of the product
        </span>
      ) : null}
      <h2 className="text-sm font-semibold uppercase tracking-wider text-ink-faint">
        {name}
      </h2>
      <p className="mt-2">
        <span className="num text-4xl font-semibold">{price}</span>{" "}
        <span className="text-sm text-ink-faint">{cadence}</span>
      </p>
      <p className="mt-3 text-sm leading-relaxed text-ink-dim">{blurb}</p>
      <ul className="mt-5 flex-1 space-y-2 text-sm text-ink-dim">
        {features.map((feature) => (
          <li key={feature} className="flex gap-2">
            <span aria-hidden="true" className="text-you">
              ✓
            </span>
            <span>{feature}</span>
          </li>
        ))}
      </ul>
    </Card>
  );
}
