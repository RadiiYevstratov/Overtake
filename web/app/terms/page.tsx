import type { Metadata } from "next";
import Link from "next/link";

import { Callout, H2, P, Prose, UL } from "@/components/prose";

export const metadata: Metadata = {
  title: "Terms",
  description: "The terms of using Overtake, in plain language.",
  alternates: { canonical: "/terms" },
};

export default function TermsPage() {
  return (
    <Prose
      title="Terms"
      updated="2 September 2026"
      lead="Plain language, because terms nobody reads protect nobody."
    >
      <Callout>
        Overtake is analysis of a free-to-enter game of skill. It is not gambling, it
        is not financial advice, and it is not affiliated with the Premier League.
      </Callout>

      <H2>What Overtake is</H2>
      <P>
        A tool that reads publicly available Fantasy Premier League data, simulates the
        rest of the season, and tells you what would improve your chances of finishing
        above the specific people in your mini-league.
      </P>

      <H2>What it is not</H2>
      <UL>
        <li>
          <strong>Not gambling.</strong> There are no odds as prices, no stakes, no
          pots, and no bookmaker links. There never will be.
        </li>
        <li>
          <strong>Not a guarantee.</strong> Projections are estimates, and we publish
          our measured error so you can see how good they are. Simulated probabilities
          are probabilities.
        </li>
        <li>
          <strong>Not connected to your FPL account.</strong> We never ask for your FPL
          password, never authenticate as you, and never write anything to your team.
        </li>
        <li>
          <strong>Not official.</strong> Overtake is not affiliated with, endorsed by,
          or associated with the Premier League or Fantasy Premier League.
        </li>
      </UL>

      <H2>Your account</H2>
      <P>
        You need to be at least 13. You are responsible for the email address on the
        account, since anyone who can read that inbox can sign in. You can delete the
        account at any time from your account page.
      </P>

      <H2>Paying</H2>
      <UL>
        <li>Pro monthly renews each month until you cancel. Cancel in one click.</li>
        <li>
          The season pass is a single payment covering August to May. It does not
          auto-renew.
        </li>
        <li>
          You have a 14-day right to withdraw under EU and UK distance-selling rules.
          We do not ask you to waive it, and we honour it on request.
        </li>
        <li>
          If a payment fails you keep full access for seven days while you fix it, and
          we never delete your data.
        </li>
      </UL>

      <H2>Fair use</H2>
      <P>
        Do not scrape the site, do not try to bypass the rate limits, and do not use
        Overtake to harass anyone. We may suspend an account that does. Requests to
        Ask-the-Gaffer are logged for 30 days so we can review abuse.
      </P>

      <H2>Availability</H2>
      <P>
        Overtake depends on an API published by a third party that owes us nothing. If
        it changes or disappears we will do our best to keep the product working, and
        will always tell you when the data you are looking at is stale rather than
        pretending otherwise.
      </P>

      <H2>Liability</H2>
      <P>
        Overtake is provided as-is. We are not liable for a fantasy football decision
        you make, or for anything that happens in your group chat as a result. Nothing
        here limits liability that cannot be limited by law.
      </P>

      <H2>Changes</H2>
      <P>
        If we change these terms materially we will email registered users. Continuing
        to use Overtake after that means the new terms apply.
      </P>

      <H2>Contact</H2>
      <P>
        <a className="underline hover:text-ink" href="mailto:hello@overtake.app">
          hello@overtake.app
        </a>
        . See also the{" "}
        <Link href="/privacy" className="underline hover:text-ink">
          privacy policy
        </Link>
        .
      </P>
    </Prose>
  );
}
