import type { Metadata } from "next";
import Link from "next/link";

import { Callout, H2, P, Prose, UL } from "@/components/prose";

export const metadata: Metadata = {
  title: "Privacy",
  description:
    "What Overtake collects, why, and how to get rid of it. Written to be understood, not to be survived.",
  alternates: { canonical: "/privacy" },
};

export default function PrivacyPage() {
  return (
    <Prose
      title="Privacy"
      updated="2 September 2026"
      lead={
        <>
          The short version: we hold your email address, an age band, your FPL manager
          ID and the leagues you track. We never ask for your FPL password. You can
          download or delete everything from your account page without emailing anyone.
        </>
      }
    >
      <Callout>
        <strong>The one-page summary.</strong> We store as little as we can get away
        with. We do not sell anything to anyone. We do not profile children. Nothing
        non-essential runs before you say yes. Everything we hold is one click away
        from being exported or deleted.
      </Callout>

      <H2>Who we are</H2>
      <P>
        Overtake is an independent product, not affiliated with or endorsed by the
        Premier League or Fantasy Premier League. Contact:{" "}
        <a className="underline hover:text-ink" href="mailto:hello@overtake.app">
          hello@overtake.app
        </a>
        .
      </P>

      <H2>What we collect about you</H2>
      <UL>
        <li>
          <strong>Your email address.</strong> It is how you sign in — there is no
          password — and how the Deadline Brief reaches you.
        </li>
        <li>
          <strong>An age band</strong>, not your date of birth. We ask for a year of
          birth, derive a band from it, and store only the band. The year itself is
          never written down.
        </li>
        <li>
          <strong>Your FPL manager ID</strong> and the leagues you choose to track, so
          we know whose squad is yours.
        </li>
        <li>
          <strong>A session cookie</strong> and, if you consent, analytics cookies.
        </li>
        <li>
          <strong>Your Ask-the-Gaffer conversations</strong>, kept for 30 days and then
          deleted.
        </li>
      </UL>
      <P>
        We do not collect your date of birth, your address, your phone number, or any
        payment details. Stripe handles cards; we never see them.
      </P>

      <H2>Data about other managers</H2>
      <P>
        Overtake analyses public data about people in your league who may not be
        Overtake users: their team name, their squad, their transfers and their
        position in the table. All of it is already published on the FPL website, and
        we do not enrich it, sell it, or use it for marketing.
      </P>
      <P>
        If you appear in someone else&apos;s Overtake league page and would rather not,
        email us with your FPL manager ID and we will suppress you from every page,
        permanently. You do not need an account to ask.
      </P>

      <H2>Why we are allowed to hold it</H2>
      <UL>
        <li>
          <strong>To give you the service you signed up for</strong> — your account,
          your leagues, your briefs. (Contract.)
        </li>
        <li>
          <strong>To keep the product working and safe</strong> — rate limiting, abuse
          prevention, and aggregate product analytics. (Legitimate interests.)
        </li>
        <li>
          <strong>Marketing email and analytics cookies</strong> — only if you say yes,
          and only if you are an adult. (Consent.)
        </li>
      </UL>

      <H2>If you are under 18</H2>
      <P>
        You need to be at least 13 to have an account. Between 13 and 17 you get the
        free plan and the full product features that run on public FPL data. We do not
        sell Pro to under-16s, we do not send you marketing email at any age under 18,
        and we do not build behavioural profiles of you.
      </P>
      <P>
        We do build behavioural profiles of FPL <em>managers</em> from their public
        transfer history — that is the product. It is analysis of publicly published
        game moves, not of a person&apos;s browsing, and it is never used to target
        anyone with advertising.
      </P>

      <H2>How long we keep things</H2>
      <UL>
        <li>Raw copies of FPL API responses: 30 days.</li>
        <li>Ask-the-Gaffer conversations and AI request logs: 30 days.</li>
        <li>Sign-in links: 15 minutes to use, deleted 7 days after they expire.</li>
        <li>Aggregate analytics events: 180 days.</li>
        <li>
          A deleted account: access ends immediately, everything is permanently purged
          within 30 days.
        </li>
      </UL>

      <H2>Who we share it with</H2>
      <P>
        Only the services that make the product run: Stripe for payments, Resend for
        email, our hosting and database providers, and an AI provider for the written
        part of the Deadline Brief. The AI provider receives computed numbers and
        first names from your league — never your email address, and never anything it
        could use to identify you.
      </P>
      <P>We do not sell your data. There is no version of this product where we do.</P>

      <H2>Your rights</H2>
      <P>
        You can export everything we hold, or delete your account outright, from{" "}
        <Link href="/app/account" className="underline hover:text-ink">
          your account page
        </Link>{" "}
        — no email, no form, no waiting. You can also object to processing, ask us to
        correct something, or complain to your national data protection authority.
      </P>

      <H2>Cookies</H2>
      <P>
        Essential cookies only, unless you accept the banner. Details are on the{" "}
        <Link href="/cookies" className="underline hover:text-ink">
          cookies page
        </Link>
        .
      </P>

      <H2>Security</H2>
      <P>
        There are no passwords in Overtake, so there is no password of yours to leak.
        Sign-in links and sessions are stored only as hashes, everything travels over
        TLS, and access to production data is limited and logged.
      </P>
    </Prose>
  );
}
