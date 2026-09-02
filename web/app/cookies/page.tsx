import type { Metadata } from "next";

import { H2, P, Prose, UL } from "@/components/prose";

export const metadata: Metadata = {
  title: "Cookies",
  description: "Exactly which cookies Overtake sets, and what each one does.",
  alternates: { canonical: "/cookies" },
};

export default function CookiesPage() {
  return (
    <Prose
      title="Cookies"
      updated="2 September 2026"
      lead="Four cookies, three of them essential. Nothing non-essential runs before you say yes."
    >
      <H2>Essential — always on</H2>
      <UL>
        <li>
          <code className="num text-ink">overtake_session</code> — keeps you signed in.
          HttpOnly, so JavaScript cannot read it. 30 days.
        </li>
        <li>
          <code className="num text-ink">overtake_csrf</code> — protects against
          cross-site request forgery. Readable by the page on purpose, because that is
          how the check works. 30 days.
        </li>
        <li>
          <code className="num text-ink">overtake_anon</code> — a random identifier
          with no personal data in it, used to count how many people reach each step.
          Never derived from your IP address. 180 days.
        </li>
      </UL>

      <H2>Optional — only after you accept</H2>
      <UL>
        <li>
          Product analytics, which help us see which parts of the product actually
          help. Declining costs you nothing: every feature works either way, and we
          still count the funnel in aggregate on our own server without a cookie.
        </li>
      </UL>

      <H2>Changing your mind</H2>
      <P>
        Clear this site&apos;s data in your browser and the banner reappears. We do not
        hide the decline button, and we do not ask again after every page.
      </P>

      <H2>What we never use</H2>
      <P>
        No advertising cookies, no cross-site trackers, no fingerprinting, and no
        third-party pixels.
      </P>
    </Prose>
  );
}
