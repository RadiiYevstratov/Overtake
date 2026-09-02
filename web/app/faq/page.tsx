import type { Metadata } from "next";
import Link from "next/link";

import { H2, P, Prose } from "@/components/prose";

export const metadata: Metadata = {
  title: "FAQ",
  description:
    "Is Overtake gambling? Is it allowed? How accurate are the projections? What happens in the summer?",
  alternates: { canonical: "/faq" },
};

const FAQ = [
  {
    q: "Is this gambling?",
    a: "No, and it never will be. There are no odds expressed as prices, no stakes, no prize pools, and no bookmaker links or sponsorship. Overtake analyses a free-to-enter game of skill and states everything as a probability against a named person.",
  },
  {
    q: "Is it allowed? Will I get banned?",
    a: "We only read pages that are already public on the FPL website. We never authenticate as you, we never write anything to your team, and we do not ask for your FPL password — if a tool ever asks you for it, that is a reason to walk away. Your FPL account is untouched by using Overtake.",
  },
  {
    q: "How accurate are the projections?",
    a: "We publish our measured error, updated as gameweeks complete, on the how-it-works page. It is not flattering and it is not meant to be: incumbents have Opta licences and we do not. Projections are an input to Overtake, not the product.",
  },
  {
    q: "How can the AI be trusted not to make things up?",
    a: "It is architecturally unable to. The model is given only numbers the simulation computed, it returns structured data rather than prose we paste in, and every number and name it writes is checked back against that input before you see it. Two failures and you get the numbers plainly with no prose at all.",
  },
  {
    q: "What happens in the summer?",
    a: "Nothing, honestly. There is no FPL season in June and July, so there is no product, so we do not charge for one. Season passes cover August to May and do not auto-renew; we email you in July when the next season is close.",
  },
  {
    q: "Can I cancel?",
    a: "One click in the billing portal, no questions and no retention offers, and you keep access to the end of the period you have paid for. Within 14 days of buying, you can have a full refund instead.",
  },
  {
    q: "Why is my probability different from last week?",
    a: "Because the inputs changed: someone transferred, prices moved, a player got injured, or a gameweek was played. The simulation is deterministic — the same inputs always produce the same odds — so if the number moved, something real moved.",
  },
  {
    q: "Someone in my league does not want to be on here.",
    a: "Email us their FPL manager ID and we will suppress them from every Overtake page permanently. They do not need an account to ask, and we do not require a reason.",
  },
  {
    q: "Does it work for head-to-head leagues?",
    a: "Not yet. Classic leagues are supported today; head-to-head is a whole format that nobody serves well and it is on the roadmap.",
  },
] as const;

export default function FaqPage() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            mainEntity: FAQ.map((item) => ({
              "@type": "Question",
              name: item.q,
              acceptedAnswer: { "@type": "Answer", text: item.a },
            })),
          }),
        }}
      />
      <Prose title="Questions people actually ask">
        {FAQ.map((item) => (
          <div key={item.q}>
            <H2>{item.q}</H2>
            <P>{item.a}</P>
          </div>
        ))}
        <div>
          <H2>Something else?</H2>
          <P>
            Email{" "}
            <a className="underline hover:text-ink" href="mailto:hello@overtake.app">
              hello@overtake.app
            </a>
            , or read{" "}
            <Link href="/how-it-works" className="underline hover:text-ink">
              how it works
            </Link>
            .
          </P>
        </div>
      </Prose>
    </>
  );
}
