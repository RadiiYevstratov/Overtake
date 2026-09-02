import Link from "next/link";

import { LeagueIdForm } from "@/components/league-id-form";
import { Card } from "@/components/ui";
import type { Guide } from "@/lib/guides";

/** One renderer for every evergreen guide, so they cannot drift apart. */
export function GuidePage({ guide, related }: { guide: Guide; related: Guide[] }) {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "Article",
            headline: guide.metaTitle,
            description: guide.description,
            author: { "@type": "Organization", name: "Overtake" },
            publisher: { "@type": "Organization", name: "Overtake" },
          }),
        }}
      />
      <article className="mx-auto max-w-2xl px-4 py-14 sm:px-6">
        <h1 className="text-4xl font-bold tracking-tight">{guide.title}</h1>
        <p className="mt-4 text-lg leading-relaxed text-ink-dim">{guide.lead}</p>

        <div className="mt-10 space-y-10">
          {guide.sections.map((section) => (
            <section key={section.heading}>
              <h2 className="text-xl font-semibold tracking-tight">{section.heading}</h2>
              <div className="mt-3 space-y-3">
                {section.body.map((paragraph, index) => (
                  <p key={index} className="leading-relaxed text-ink-dim">
                    {paragraph}
                  </p>
                ))}
              </div>
            </section>
          ))}
        </div>

        <Card className="mt-12 p-6">
          <h2 className="text-lg font-semibold">See it for your own league</h2>
          <p className="mt-2 leading-relaxed text-ink-dim">
            Paste your league ID. No signup, no FPL password.
          </p>
          <div className="mt-4">
            <LeagueIdForm />
          </div>
        </Card>

        {related.length > 0 ? (
          <nav aria-label="Related guides" className="mt-12">
            <h2 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-faint">
              Read next
            </h2>
            <ul className="mt-3 space-y-2">
              {related.map((item) => (
                <li key={item.href}>
                  <Link href={item.href} className="text-ink-dim hover:text-ink">
                    {item.title} →
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        ) : null}
      </article>
    </>
  );
}
