import Link from "next/link";

import { LeagueIdForm } from "@/components/league-id-form";

export default function NotFound() {
  return (
    <div className="mx-auto max-w-xl px-4 py-20 sm:px-6">
      <h1 className="text-4xl font-bold tracking-tight">Nothing here</h1>
      <p className="mt-4 leading-relaxed text-ink-dim">
        That page does not exist, or the league ID was not one we can read. Overtake
        handles classic mini-leagues of 200 managers or fewer.
      </p>
      <div className="mt-8">
        <LeagueIdForm />
      </div>
      <p className="mt-6 text-sm text-ink-faint">
        Not sure where to find your league ID?{" "}
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
