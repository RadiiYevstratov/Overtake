import Link from "next/link";

import { AccountSettings } from "@/components/account-settings";
import { BillingActions } from "@/components/billing-actions";
import { DangerZone } from "@/components/danger-zone";
import { Badge, Card, RuleHeading } from "@/components/ui";
import { serverFetchOrNull } from "@/lib/api";
import { shortDate } from "@/lib/format";
import type { Me } from "@/lib/types";

export default async function AccountPage() {
  const me = (await serverFetchOrNull<Me>("/me"))!;
  const { plan, user, limits, usage } = me;

  return (
    <>
      <h1 className="text-3xl font-bold tracking-tight">Account</h1>

      {/* ---------------------------------------------------------- plan */}
      <section className="mt-8">
        <RuleHeading>Your plan</RuleHeading>
        <Card className="p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-xl font-semibold">{plan.label}</h2>
                {plan.in_grace_period ? <Badge tone="warn">Payment failed</Badge> : null}
                {plan.cancel_at_period_end ? <Badge>Ending</Badge> : null}
              </div>
              {plan.is_pro ? (
                <p className="mt-2 text-ink-dim">
                  {plan.source === "season_pass" ? (
                    <>
                      Your season pass runs to{" "}
                      <span className="num text-ink">
                        {shortDate(plan.season_pass_ends_at)}
                      </span>
                      . It does not auto-renew — we will email you in July.
                    </>
                  ) : plan.cancel_at_period_end && plan.current_period_end ? (
                    <>
                      Pro until{" "}
                      <span className="num text-ink">
                        {shortDate(plan.current_period_end)}
                      </span>
                      . Nothing changes until then.
                    </>
                  ) : plan.current_period_end ? (
                    <>
                      Renews on{" "}
                      <span className="num text-ink">
                        {shortDate(plan.current_period_end)}
                      </span>
                      .
                    </>
                  ) : null}
                </p>
              ) : (
                <p className="mt-2 max-w-xl text-ink-dim">
                  You have the free plan: one league, the full league board, and one
                  rival dossier a season.
                </p>
              )}
            </div>
            <BillingActions isPro={plan.is_pro} canPurchase={user.age_band !== "13_15"} />
          </div>

          <dl className="mt-6 grid grid-cols-2 gap-4 border-t border-border pt-5 text-sm sm:grid-cols-4">
            <Usage
              label="Dossiers this season"
              used={usage.dossiers_this_season ?? 0}
              limit={limits.dossiers_per_season}
            />
            <Usage
              label="Gaffer questions today"
              used={usage.gaffer_messages_today ?? 0}
              limit={limits.gaffer_messages_per_day}
            />
            <Usage label="Leagues" used={0} limit={limits.leagues} showUsed={false} />
            <div>
              <dt className="text-xs text-ink-faint">Scenarios per gameweek</dt>
              <dd className="num mt-0.5">
                {limits.scenarios_per_gameweek ?? "unlimited"}
              </dd>
            </div>
          </dl>

          {plan.is_pro ? (
            <p className="mt-5 text-sm text-ink-faint">
              Cancelling takes one click in the billing portal. There is no retention
              interrogation, and you keep access until the end of the period you have
              paid for.
            </p>
          ) : null}
        </Card>
      </section>

      {/* ------------------------------------------------------- profile */}
      <section className="mt-10">
        <RuleHeading>Your details</RuleHeading>
        <AccountSettings me={me} />
      </section>

      {/* -------------------------------------------------------- privacy */}
      <section className="mt-10">
        <RuleHeading>Your data</RuleHeading>
        <Card className="p-6">
          <p className="max-w-2xl leading-relaxed text-ink-dim">
            We hold your email address, an age band, your FPL manager ID and the
            leagues you track. We do not hold your date of birth, your address, your
            phone number or any payment details — Stripe handles cards, and we never
            see them.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <a
              href="/api/v1/me/export"
              className="inline-flex min-h-[44px] items-center rounded-[8px] border border-border-strong px-4 py-2.5 text-sm transition-colors hover:border-ink-faint"
            >
              Download everything we hold
            </a>
            <Link
              href="/privacy"
              className="inline-flex min-h-[44px] items-center rounded-[8px] px-4 py-2.5 text-sm text-ink-dim transition-colors hover:text-ink"
            >
              Read the privacy policy
            </Link>
          </div>
        </Card>
      </section>

      <section className="mt-10">
        <RuleHeading>Danger zone</RuleHeading>
        <DangerZone />
      </section>
    </>
  );
}

function Usage({
  label,
  used,
  limit,
  showUsed = true,
}: {
  label: string;
  used: number;
  limit: number | null;
  showUsed?: boolean;
}) {
  return (
    <div>
      <dt className="text-xs text-ink-faint">{label}</dt>
      <dd className="num mt-0.5">
        {limit === null ? (
          "unlimited"
        ) : showUsed ? (
          <>
            {used}
            <span className="text-ink-faint"> / {limit}</span>
          </>
        ) : (
          limit
        )}
      </dd>
    </div>
  );
}
