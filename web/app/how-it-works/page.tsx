import type { Metadata } from "next";

import { LeagueIdForm } from "@/components/league-id-form";
import { Card, RuleHeading } from "@/components/ui";
import { serverFetchOrNull } from "@/lib/api";
import type { SeasonMeta } from "@/lib/types";

export const metadata: Metadata = {
  title: "How it works",
  description:
    "How Overtake simulates the rest of your FPL season against your rivals' real squads — and how accurate the projections underneath it actually are.",
  alternates: { canonical: "/how-it-works" },
};

export const revalidate = 3600;

export default async function HowItWorksPage() {
  const meta = await serverFetchOrNull<SeasonMeta>("/meta/season", { revalidate: 300 });
  const accuracy = meta?.accuracy;
  const nSims = (meta?.simulations.n_sims ?? 20000).toLocaleString("en-GB");

  return (
    <div className="mx-auto max-w-3xl px-4 py-14 sm:px-6">
      <h1 className="text-4xl font-bold tracking-tight">How it works</h1>
      <p className="mt-4 text-lg leading-relaxed text-ink-dim">
        Four layers. Only one of them is an AI, and it is the last one — it reads the
        numbers, it never produces them.
      </p>

      <ol className="mt-10 space-y-6">
        <Layer
          n="1"
          title="We read the public FPL API"
          body="Every manager's squad, transfers, chips and standings are published by the FPL website without a login. We read them politely — never more than twice a second, always with a contact address in the request — and we cache everything. We never ask for your FPL password, and we have no write access to anything."
        />
        <Layer
          n="2"
          title="We project every player"
          body="Expected points per player per gameweek, with an explicit probability that they start at all. This is deliberately the least clever part of the stack: we shrink hard toward a price-and-position baseline so two good weeks do not fool the model, and we publish the measured error rather than claiming accuracy we do not have."
        />
        <Layer
          n="3"
          title="We simulate the rest of the season"
          body={`${nSims} times, over every manager's actual squad, with teammates' scores correlated the way they really are and with the projection model's own uncertainty carried through. The output is not "who scores most" — it is the probability that you finish above each specific person.`}
        />
        <Layer
          n="4"
          title="The AI writes it up"
          body="A distribution does not change anyone's behaviour. The AI turns the simulation into one named, specific argument you can act on. It is given only computed numbers, it returns structured data, and every figure it writes is checked back against the simulation before you ever see it. If that check fails twice, you get the numbers plainly instead. The product is allowed to be less impressive; it is never allowed to be wrong."
        />
      </ol>

      <section className="mt-14">
        <RuleHeading>How accurate are the projections?</RuleHeading>
        <Card className="p-6">
          {accuracy?.mae != null ? (
            <>
              <p className="text-lg">
                Our current mean absolute error is{" "}
                <span className="num font-semibold text-ink">
                  {accuracy.mae.toFixed(2)}
                </span>{" "}
                points per player per gameweek, measured out-of-sample over the last{" "}
                <span className="num">{accuracy.gameweeks}</span> completed gameweek
                {accuracy.gameweeks === 1 ? "" : "s"}.
              </p>
              {accuracy.per_gameweek?.length ? (
                <div className="scroll-x mt-5">
                  <table className="w-full border-collapse text-sm">
                    <caption className="sr-only">
                      Measured projection error by gameweek
                    </caption>
                    <thead>
                      <tr className="border-b border-border text-left text-[11px] uppercase tracking-wider text-ink-faint">
                        <th scope="col" className="py-2 pr-4 font-semibold">
                          Gameweek
                        </th>
                        <th scope="col" className="py-2 pr-4 text-right font-semibold">
                          MAE
                        </th>
                        <th scope="col" className="py-2 text-right font-semibold">
                          Players
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {accuracy.per_gameweek.map((row) => (
                        <tr key={row.gameweek} className="border-b border-border/60">
                          <td className="num py-2 pr-4">GW{row.gameweek}</td>
                          <td className="num py-2 pr-4 text-right">
                            {row.mae.toFixed(2)}
                          </td>
                          <td className="num py-2 text-right text-ink-dim">{row.n}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : null}
            </>
          ) : (
            <p className="text-ink-dim">
              Not enough completed gameweeks have been played yet to measure our error
              honestly. This number appears as soon as there is one, and it is not
              hidden when it is unflattering.
            </p>
          )}
          <p className="mt-5 text-sm leading-relaxed text-ink-faint">
            For context: incumbent FPL tools have Opta data licences and we do not, so
            their projections will beat ours. That is fine — projections are an input
            here, not the product. The thing nobody else computes is the probability
            that you finish above a named person, and that depends far more on the
            simulation than on the last decimal place of a projection.
          </p>
        </Card>
      </section>

      <section className="mt-14">
        <RuleHeading>Why not just maximise expected points?</RuleHeading>
        <p className="leading-relaxed text-ink-dim">
          Because it is the wrong objective for almost everyone. If you are forty points
          behind with six gameweeks left, the highest-expected-points move is usually
          the move that keeps you forty points behind: it is what your rival is doing
          too. What you need is variance they are not exposed to — and if you are ahead,
          the opposite. Overtake is the only tool that computes which of those you are
          in, against each specific person.
        </p>
      </section>

      <section className="mt-14">
        <RuleHeading>Try it</RuleHeading>
        <LeagueIdForm />
      </section>
    </div>
  );
}

function Layer({ n, title, body }: { n: string; title: string; body: string }) {
  return (
    <li>
      <Card className="p-6">
        <div className="num text-sm font-semibold text-you">Layer {n}</div>
        <h2 className="mt-2 text-xl font-semibold">{title}</h2>
        <p className="mt-2 leading-relaxed text-ink-dim">{body}</p>
      </Card>
    </li>
  );
}
