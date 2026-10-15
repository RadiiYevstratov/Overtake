import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { LeagueIdForm } from "@/components/league-id-form";
import { leagueIdError, parseLeagueId } from "@/lib/format";

export const metadata: Metadata = {
  title: "Find your league",
  robots: { index: false, follow: false },
};

type Search = Promise<{ league?: string | string[] }>;

/**
 * Where the league form submits when the browser does it without JavaScript —
 * on a slow phone, before the page has finished loading. With JavaScript the
 * form navigates itself and never comes here.
 */
export default async function LeagueLookupPage({ searchParams }: { searchParams: Search }) {
  const { league } = await searchParams;
  const value = (Array.isArray(league) ? league[0] : league) ?? "";
  const leagueId = parseLeagueId(value);
  if (leagueId !== null) redirect(`/l/${leagueId}`);

  return (
    <div className="mx-auto max-w-xl px-4 py-20 sm:px-6">
      <h1 className="text-3xl font-bold tracking-tight">Which league?</h1>
      <p className="mt-4 leading-relaxed text-ink-dim">
        Paste your league ID, or the whole URL of the league from the FPL site.
      </p>
      <div className="mt-8">
        <LeagueIdForm autoFocus initialValue={value} initialError={leagueIdError(value)} />
      </div>
      <p className="mt-6 text-sm text-ink-faint">
        Not sure where to find it?{" "}
        <Link
          href="/how-to/find-your-fpl-league-id"
          className="underline hover:text-ink-dim"
        >
          It takes thirty seconds
        </Link>
        .
      </p>
    </div>
  );
}
