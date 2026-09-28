import Link from "next/link";
import { notFound } from "next/navigation";

import { Badge, Card, EmptyState, RuleHeading } from "@/components/ui";
import { serverFetchOrNull } from "@/lib/api";
import type { FunnelReport, FunnelThreshold } from "@/lib/types";

/**
 * The weekly scorecard, in words rather than JSON.
 *
 * The same numbers as /api/v1/analytics/funnel, which is admin-only: a
 * non-admin (or a signed-out visitor) gets a 404 here rather than a hint that
 * the page exists at all.
 */
export const metadata = {
  title: "Scorecard — Overtake",
  robots: { index: false, follow: false },
};

// Always fresh: a cached scorecard is worse than no scorecard.
export const dynamic = "force-dynamic";

const WINDOWS = [7, 14, 30, 90] as const;

/** The funnel in the order a person actually walks it. */
const STEPS = [
  {
    key: "league_board_viewed",
    label: "Saw their league's odds",
    note: "The first real value, and no sign-up needed",
  },
  {
    key: "dossier_viewed",
    label: "Opened a rival's dossier",
    note: "Curiosity about one named person",
  },
  {
    key: "aha_reached",
    label: "Read past “where the gap is”",
    note: "The aha moment",
  },
  { key: "signup_completed", label: "Created an account", note: null },
  { key: "paywall_shown", label: "Hit the paywall", note: null },
  { key: "checkout_started", label: "Started checkout", note: null },
  { key: "checkout_completed", label: "Paid", note: null },
] as const;

const METRICS = [
  {
    key: "aha_rate",
    label: "Aha rate",
    meaning: "Of the people who opened a dossier, how many read the gap",
  },
  {
    key: "share_rate",
    label: "Share rate",
    meaning: "Of the people who opened a dossier, how many pressed share",
  },
  {
    key: "paywall_click_through",
    label: "Paywall click-through",
    meaning: "Of the people who hit the paywall, how many started checkout",
  },
  {
    key: "paid_conversion",
    label: "Paid conversion",
    meaning: "Of the people who signed up, how many paid",
  },
] as const;

function percent(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const scaled = value * 100;
  // Below 10% a rounded whole number hides the difference between 1% and 4%.
  return `${scaled < 10 ? scaled.toFixed(1) : Math.round(scaled)}%`;
}

function verdict(
  threshold: FunnelThreshold,
): { label: string; tone: "neutral" | "you" | "rival" | "warn" } {
  const { value, go, no_go: noGo } = threshold;
  if (value === null) return { label: "No data yet", tone: "neutral" };
  if (value >= go) return { label: "On target", tone: "you" };
  // A zero no-go band (paid conversion) means any sale at all beats "stop".
  if (value < noGo || (noGo === 0 && value === 0))
    return { label: "Below the line", tone: "rival" };
  return { label: "Worth watching", tone: "warn" };
}

export default async function FunnelPage({
  searchParams,
}: {
  searchParams: Promise<{ days?: string; me?: string }>;
}) {
  const { days, me } = await searchParams;
  const requested = Number.parseInt(days ?? "7", 10);
  const windowDays = WINDOWS.includes(requested as (typeof WINDOWS)[number])
    ? requested
    : 7;
  // Your own testing is hidden by default; ?me=1 puts it back for one look.
  const includeMine = me === "1";

  const report = await serverFetchOrNull<FunnelReport>(
    `/analytics/funnel?days=${windowDays}${includeMine ? "&include_internal=true" : ""}`,
  );
  // Forbidden and unauthenticated both arrive as null. Neither should confirm
  // that an admin page lives here.
  if (!report) notFound();

  const steps = STEPS.map((step) => ({
    ...step,
    people: report.funnel[step.key] ?? 0,
  }));
  const top = Math.max(...steps.map((step) => step.people), 0);
  const totals = report.by_source.reduce(
    (sum, row) => ({
      visitors: sum.visitors + row.visitors,
      boards: sum.boards + row.league_board_viewed,
      signups: sum.signups + row.signup_completed,
      paid: sum.paid + row.checkout_completed,
    }),
    { visitors: 0, boards: 0, signups: 0, paid: 0 },
  );
  const since = new Date(Date.now() - windowDays * 86_400_000).toLocaleDateString(
    "en-GB",
    { day: "numeric", month: "long" },
  );

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Scorecard</h1>
          <p className="mt-2 text-ink-dim">
            Everyone who used Overtake since{" "}
            <span className="num text-ink">{since}</span>. Each number counts
            people, not clicks.
          </p>
          <p className="mt-2 text-sm text-ink-faint">
            {report.internal.included ? (
              <>
                Showing your own testing as well.{" "}
                <Link
                  href={`/app/funnel?days=${windowDays}`}
                  className="text-you underline"
                >
                  Hide it
                </Link>
              </>
            ) : (
              <>
                Your own testing is left out:{" "}
                <span className="num text-ink-dim">
                  {report.internal.hidden_events}
                </span>{" "}
                events from{" "}
                <span className="num text-ink-dim">
                  {report.internal.browsers}
                </span>{" "}
                {report.internal.browsers === 1 ? "browser" : "browsers"}.{" "}
                <Link
                  href={`/app/funnel?days=${windowDays}&me=1`}
                  className="text-you underline"
                >
                  Show it
                </Link>
              </>
            )}
          </p>
        </div>
        <nav aria-label="Time window" className="flex gap-2">
          {WINDOWS.map((option) => (
            <Link
              key={option}
              href={`/app/funnel?days=${option}${includeMine ? "&me=1" : ""}`}
              aria-current={option === windowDays ? "page" : undefined}
              className={
                option === windowDays
                  ? "num rounded-[8px] border border-you-dim bg-surface-2 px-3 py-2 text-sm text-you"
                  : "num rounded-[8px] border border-border px-3 py-2 text-sm text-ink-dim hover:border-border-strong hover:text-ink"
              }
            >
              {option}d
            </Link>
          ))}
        </nav>
      </div>

      {top === 0 ? (
        <div className="mt-8">
          <EmptyState title="Nobody has used it in this window">
            Share a tagged link — the ones in{" "}
            <span className="num">YOUR_TASKS.md</span> — and this page fills in
            as people arrive. Your own visits count too, so paste a league ID to
            check the tracking works.
          </EmptyState>
        </div>
      ) : null}

      <section className="mt-10">
        <RuleHeading>The four decisions</RuleHeading>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {METRICS.map((metric) => {
            const threshold = report.thresholds[metric.key];
            const call = verdict(threshold);
            return (
              <Card key={metric.key} className="flex flex-col gap-3 p-4">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-sm font-semibold">{metric.label}</h3>
                  <Badge tone={call.tone}>{call.label}</Badge>
                </div>
                <div
                  className={
                    call.tone === "you"
                      ? "num text-4xl font-semibold text-you"
                      : call.tone === "rival"
                        ? "num text-4xl font-semibold text-rival"
                        : "num text-4xl font-semibold text-ink"
                  }
                >
                  {percent(threshold.value)}
                </div>
                <p className="text-xs leading-snug text-ink-faint">
                  {metric.meaning}
                </p>
                <p className="num text-[11px] text-ink-faint">
                  target {percent(threshold.go)} · stop below{" "}
                  {percent(threshold.no_go)}
                </p>
              </Card>
            );
          })}
        </div>
      </section>

      <section className="mt-10">
        <RuleHeading>Where people drop out</RuleHeading>
        <Card className="divide-y divide-border">
          {steps.map((step, index) => {
            const previous = index === 0 ? null : (steps[index - 1]?.people ?? null);
            const kept =
              previous && previous > 0 ? step.people / previous : null;
            return (
              <div key={step.key} className="p-4">
                <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
                  <span className="text-sm font-medium">{step.label}</span>
                  <span className="flex items-baseline gap-3">
                    <span className="num text-lg font-semibold">
                      {step.people}
                    </span>
                    {kept === null ? null : (
                      <span
                        className={
                          kept < 0.25
                            ? "num text-xs text-rival"
                            : "num text-xs text-ink-faint"
                        }
                      >
                        {percent(kept)} of the step above
                      </span>
                    )}
                  </span>
                </div>
                <div
                  className="mt-2 h-1.5 rounded-full bg-surface-2"
                  aria-hidden="true"
                >
                  <div
                    className="h-full rounded-full bg-you-dim"
                    style={{
                      width: `${top === 0 ? 0 : (step.people / top) * 100}%`,
                    }}
                  />
                </div>
                {step.note ? (
                  <p className="mt-1.5 text-xs text-ink-faint">{step.note}</p>
                ) : null}
              </div>
            );
          })}
        </Card>
      </section>

      <section className="mt-10">
        <RuleHeading>Which channel is worth your twenty minutes</RuleHeading>
        {report.by_source.length === 0 ? (
          <EmptyState title="No sources recorded yet">
            A visitor&apos;s first source is kept for the whole visit. Untagged
            links show up as <span className="num">direct</span>.
          </EmptyState>
        ) : (
          <Card className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-sm">
              <thead>
                <tr className="text-[11px] uppercase tracking-[0.12em] text-ink-faint">
                  <th className="px-4 py-3 text-left font-semibold">Source</th>
                  <th className="px-4 py-3 text-right font-semibold">
                    Visitors
                  </th>
                  <th className="px-4 py-3 text-right font-semibold">Boards</th>
                  <th className="px-4 py-3 text-right font-semibold">
                    Sign-ups
                  </th>
                  <th className="px-4 py-3 text-right font-semibold">Paid</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {report.by_source.map((row) => (
                  <tr key={row.source}>
                    <td className="px-4 py-3 font-medium">{row.source}</td>
                    <td className="num px-4 py-3 text-right">{row.visitors}</td>
                    <td className="num px-4 py-3 text-right">
                      {row.league_board_viewed}
                      <span className="ml-2 text-xs text-ink-faint">
                        {row.visitors
                          ? percent(row.league_board_viewed / row.visitors)
                          : "—"}
                      </span>
                    </td>
                    <td className="num px-4 py-3 text-right">
                      {row.signup_completed}
                    </td>
                    <td
                      className={
                        row.checkout_completed > 0
                          ? "num px-4 py-3 text-right text-you"
                          : "num px-4 py-3 text-right"
                      }
                    >
                      {row.checkout_completed}
                    </td>
                  </tr>
                ))}
                <tr className="border-t border-border-strong text-ink-dim">
                  <td className="px-4 py-3 font-medium">All sources</td>
                  <td className="num px-4 py-3 text-right">
                    {totals.visitors}
                  </td>
                  <td className="num px-4 py-3 text-right">{totals.boards}</td>
                  <td className="num px-4 py-3 text-right">{totals.signups}</td>
                  <td className="num px-4 py-3 text-right">{totals.paid}</td>
                </tr>
              </tbody>
            </table>
          </Card>
        )}
      </section>

      <section className="mt-10">
        <RuleHeading>Everything recorded</RuleHeading>
        <details className="rounded-[8px] border border-border bg-surface">
          <summary className="cursor-pointer px-4 py-3 text-sm text-ink-dim hover:text-ink">
            Every event in this window, people and total times
          </summary>
          <div className="overflow-x-auto border-t border-border">
            <table className="w-full min-w-[420px] text-sm">
              <thead>
                <tr className="text-[11px] uppercase tracking-[0.12em] text-ink-faint">
                  <th className="px-4 py-3 text-left font-semibold">Event</th>
                  <th className="px-4 py-3 text-right font-semibold">People</th>
                  <th className="px-4 py-3 text-right font-semibold">Times</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {Object.entries(report.counts)
                  .sort((a, b) => b[1].uniques - a[1].uniques)
                  .map(([name, count]) => (
                    <tr key={name}>
                      <td className="num px-4 py-3 text-ink-dim">{name}</td>
                      <td className="num px-4 py-3 text-right">
                        {count.uniques}
                      </td>
                      <td className="num px-4 py-3 text-right text-ink-faint">
                        {count.events}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </details>
        <p className="mt-3 text-xs text-ink-faint">
          Same numbers as{" "}
          <span className="num">/api/v1/analytics/funnel?days={windowDays}</span>,
          which still returns JSON.
        </p>
      </section>
    </>
  );
}
