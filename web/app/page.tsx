import type { Metadata } from "next";
import Link from "next/link";

import { LeagueIdForm } from "@/components/league-id-form";
import { Card, ProvenanceFooter, RuleHeading } from "@/components/ui";
import { serverFetchOrNull } from "@/lib/api";
import type { SeasonMeta } from "@/lib/types";

export const metadata: Metadata = {
  title: "Overtake — beat the people in your FPL mini-league",
  description:
    "Every other FPL tool optimises your global rank. Nobody has a global rank framed on their wall. Overtake works out what it takes to finish above the specific people you actually play against.",
  alternates: { canonical: "/" },
  openGraph: {
    title: "Stop trying to beat 13 million strangers.",
    description:
      "Start beating the eight people in your league. Paste your league ID — no signup, no FPL password.",
    url: "/",
  },
};

export const revalidate = 3600;

export default async function LandingPage() {
  const meta = await serverFetchOrNull<SeasonMeta>("/meta/season", {
    revalidate: 300,
  });

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd()) }}
      />

      {/* ---------------------------------------------------------- hero */}
      <section className="mx-auto max-w-6xl px-4 pb-4 pt-14 sm:px-6 sm:pt-20">
        <div className="max-w-3xl">
          <h1 className="text-4xl font-bold leading-[1.08] tracking-tight sm:text-6xl">
            Stop trying to beat 13 million strangers.
            <span className="mt-2 block text-you">
              Start beating the eight people in your league.
            </span>
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-ink-dim">
            Every other FPL tool optimises your global rank. Nobody has a global rank
            framed on their wall. Overtake works out what it takes to finish above the
            specific people you actually play against.
          </p>
        </div>

        <div className="mt-9 max-w-2xl">
          <LeagueIdForm />
          <p className="mt-3 text-sm text-ink-faint">
            No signup. No FPL password. Ever.{" "}
            <Link
              href="/how-to/find-your-fpl-league-id"
              className="underline underline-offset-2 hover:text-ink-dim"
            >
              Where do I find my league ID?
            </Link>
          </p>
        </div>

        <WorkedExample meta={meta} />
      </section>

      {/* ------------------------------------------------------- problem */}
      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <div className="grid gap-10 md:grid-cols-2 md:gap-16">
          <div>
            <RuleHeading>The problem</RuleHeading>
            <p className="text-xl leading-relaxed text-ink">
              You&apos;re 40 points behind. So you read the tips, you buy the template,
              and you finish 40 points behind.
            </p>
            <p className="mt-4 text-lg leading-relaxed text-ink-dim">
              Copying the field is how you stay where you are.
            </p>
          </div>
          <div>
            <RuleHeading>What Overtake does</RuleHeading>
            <p className="text-lg leading-relaxed text-ink-dim">
              Overtake reads your league from the official FPL API, simulates the
              remaining season{" "}
              <span className="num text-ink">
                {(meta?.simulations.n_sims ?? 20000).toLocaleString("en-GB")}
              </span>{" "}
              times against every rival&apos;s real squad, and ranks your options by how
              much they close the gap — not by expected points.
            </p>
          </div>
        </div>
      </section>

      {/* ---------------------------------------------------- how it works */}
      <section className="border-y border-border bg-surface/40">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <RuleHeading>How it works</RuleHeading>
          <ol className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                n: "1",
                title: "Paste your league ID",
                body: "Or the URL from the FPL site. No account needed to see your odds.",
              },
              {
                n: "2",
                title: "We pull every rival's squad",
                body: "From the public FPL API. Read-only, and never your password.",
              },
              {
                n: "3",
                title: "We simulate the rest of the season",
                body: "Twenty thousand times, against their actual players and chips.",
              },
              {
                n: "4",
                title: "You get one clear move",
                body: "Before each deadline, with what it costs if it goes wrong.",
              },
            ].map((step) => (
              <li key={step.n}>
                <Card className="h-full p-5">
                  <div className="num text-sm font-semibold text-you">{step.n}</div>
                  <h3 className="mt-3 font-semibold text-ink">{step.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-ink-dim">
                    {step.body}
                  </p>
                </Card>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* ------------------------------------------------------------- AI */}
      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <div className="grid gap-10 md:grid-cols-2 md:gap-16">
          <div>
            <RuleHeading>The AI part, honestly</RuleHeading>
            <p className="text-lg leading-relaxed text-ink-dim">
              The maths is a simulation, not a chatbot. The AI&apos;s job is to tell you
              what the simulation means, in a sentence you can act on before the
              deadline.{" "}
              <span className="text-ink">
                It never invents a number: every figure in every brief is checked against
                the simulation that produced it.
              </span>{" "}
              If that check fails, you get the numbers plainly instead of prose. The
              product is allowed to be less impressive. It is never allowed to be wrong.
            </p>
          </div>
          <div>
            <RuleHeading>What we never do</RuleHeading>
            <ul className="space-y-3 text-lg leading-relaxed text-ink-dim">
              <li>
                <span className="text-ink">We never ask for your FPL password.</span> We
                only read data that is already public on the FPL website.
              </li>
              <li>
                <span className="text-ink">We never touch your team.</span> Overtake has
                no write access to anything.
              </li>
              <li>
                <span className="text-ink">This is not gambling.</span> No odds as
                prices, no stakes, no bookmakers. Ever.
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* -------------------------------------------------------- pricing */}
      <section className="border-y border-border bg-surface/40">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <RuleHeading>Pricing</RuleHeading>
          <div className="grid gap-4 md:grid-cols-3">
            <PlanCard
              name="Free"
              price="€0"
              cadence="always"
              features={[
                "One league",
                "Live league board with win probabilities",
                "One rival dossier a season",
                "Shareable league card",
              ]}
            />
            <PlanCard
              name="Pro monthly"
              price="€4.99"
              cadence="a month"
              features={[
                "Every rival, every league",
                "Deadline Brief, in-app and by email",
                "The Overtake Simulator",
                "Chip planner and Ask-the-Gaffer",
              ]}
            />
            <PlanCard
              name="Season pass"
              price="€29.99"
              cadence="August to May"
              highlight
              features={[
                "Everything in Pro",
                "One payment, no renewal decision",
                "No auto-renew, no surprises",
                "Cheaper than one bad −8 hit",
              ]}
            />
          </div>
          <p className="mt-5 text-sm text-ink-faint">
            Cancel in one click and keep access to the end of the period. Full refund on
            request within 14 days, no questions.
          </p>
        </div>
      </section>

      {/* ------------------------------------------------------------ FAQ */}
      <section className="mx-auto max-w-3xl px-4 py-16 sm:px-6">
        <RuleHeading>Questions people actually ask</RuleHeading>
        <dl className="space-y-6">
          {FAQ.map((item) => (
            <div key={item.q}>
              <dt className="font-semibold text-ink">{item.q}</dt>
              <dd className="mt-1.5 leading-relaxed text-ink-dim">{item.a}</dd>
            </div>
          ))}
        </dl>
      </section>

      {/* ------------------------------------------------------ final CTA */}
      <section className="mx-auto max-w-3xl px-4 pb-20 text-center sm:px-6">
        <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Paste your league ID. See who you can still catch.
        </h2>
        <div className="mx-auto mt-8 max-w-xl text-left">
          <LeagueIdForm />
        </div>
      </section>
    </>
  );
}

function WorkedExample({ meta }: { meta: SeasonMeta | null }) {
  return (
    <Card className="mt-12 max-w-2xl p-5">
      <div className="mb-4 flex items-center gap-3">
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-faint">
          Live example
        </span>
        <span className="h-px flex-1 bg-border" aria-hidden="true" />
      </div>
      <p className="text-lg leading-relaxed">
        You are <span className="num font-semibold text-rival">18%</span> to finish above
        Dan · <span className="num font-semibold text-you">71%</span> above Priya
      </p>
      <p className="mt-2 leading-relaxed text-ink-dim">
        Catching Dan needs <span className="num text-ink">+3.7</span> pts/GW. One move
        gets you 60% of the way there.
      </p>
      <div className="mt-4 border-t border-border pt-3">
        <ProvenanceFooter
          nSims={meta?.simulations.n_sims ?? 20000}
          seed={meta?.simulations.seed ?? 8814}
          computedAt="this example"
          mae={meta?.accuracy.mae ?? null}
          maeGameweeks={meta?.accuracy.gameweeks ?? 0}
        />
      </div>
    </Card>
  );
}

function PlanCard({
  name,
  price,
  cadence,
  features,
  highlight,
}: {
  name: string;
  price: string;
  cadence: string;
  features: string[];
  highlight?: boolean;
}) {
  return (
    <Card
      className={`flex h-full flex-col p-6 ${highlight ? "border-you-dim" : ""}`}
    >
      {highlight ? (
        <span className="mb-3 inline-flex w-fit rounded-full border border-you-dim px-2.5 py-1 text-[11px] font-medium text-you">
          Most people pick this
        </span>
      ) : null}
      <h3 className="text-sm font-semibold uppercase tracking-wider text-ink-faint">
        {name}
      </h3>
      <p className="mt-2">
        <span className="num text-3xl font-semibold text-ink">{price}</span>{" "}
        <span className="text-sm text-ink-faint">{cadence}</span>
      </p>
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
      <Link
        href="/pricing"
        className="mt-6 inline-flex min-h-[44px] items-center justify-center rounded-[8px] border border-border-strong px-4 py-2.5 text-sm transition-colors hover:border-ink-faint"
      >
        See full pricing
      </Link>
    </Card>
  );
}

const FAQ = [
  {
    q: "Is this gambling?",
    a: "No. There are no odds as prices, no stakes, no pots and no bookmaker links, and there never will be. Overtake analyses a free-to-enter game of skill and expresses everything as a probability against a named person.",
  },
  {
    q: "Is it allowed?",
    a: "We only read pages that are already public on the FPL website, we never authenticate as you, and we never write anything to your account. We do not ask for your FPL password and would refuse it if offered.",
  },
  {
    q: "How accurate are the projections?",
    a: "Honestly: they are the weakest part of the stack, and we publish our measured error next to every number so you can judge for yourself. We do not compete with Opta-licensed projections — projections are an input here, and rival-relative simulation is the product.",
  },
  {
    q: "What happens in the summer?",
    a: "Season passes cover August to May. There is no product in June and July, so we do not charge for it, and we will email you in July when the next season is close.",
  },
  {
    q: "Can I cancel?",
    a: "One click in the billing portal, no retention interrogation, and you keep access to the end of the period you paid for.",
  },
] as const;

function faqJsonLd() {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: FAQ.map((item) => ({
      "@type": "Question",
      name: item.q,
      acceptedAnswer: { "@type": "Answer", text: item.a },
    })),
  };
}
