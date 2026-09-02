import Link from "next/link";

import { Card, Probability, cx } from "@/components/ui";
import { signedInt, varianceCopy } from "@/lib/format";
import type { LeagueBoardRow } from "@/lib/types";

const FREE_UNLOCKED = 1;

/**
 * Three rival cards below the board. The first is open; the rest are blurred
 * with a label that names the specific rival — "Unlock Dan's dossier", never
 * "Upgrade to Pro". Specificity is the product.
 */
export function RivalCards({
  leagueId,
  you,
  rows,
  isPro,
  signedIn,
}: {
  leagueId: number;
  you: number;
  rows: LeagueBoardRow[];
  isPro: boolean;
  signedIn: boolean;
}) {
  // Rivals above you, hardest-but-catchable first; then those you are holding off.
  const ahead = rows
    .filter((row) => (row.odds_vs_you?.gap_now ?? 0) < 0)
    .sort((a, b) => (b.odds_vs_you?.p_above ?? 0) - (a.odds_vs_you?.p_above ?? 0));
  const behind = rows
    .filter((row) => (row.odds_vs_you?.gap_now ?? 0) >= 0)
    .sort((a, b) => (a.odds_vs_you?.p_above ?? 1) - (b.odds_vs_you?.p_above ?? 1));
  const ordered = [...ahead, ...behind].slice(0, 3);

  if (ordered.length === 0) {
    return (
      <Card className="p-6 text-sm text-ink-dim">
        No rival comparisons yet — squads become public once a deadline has passed.
      </Card>
    );
  }

  return (
    <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {ordered.map((row, index) => {
        const odds = row.odds_vs_you;
        if (!odds) return null;
        const locked = !isPro && index >= FREE_UNLOCKED;
        return (
          <li key={row.manager.entry_id}>
            <RivalCard
              leagueId={leagueId}
              you={you}
              row={row}
              locked={locked}
              signedIn={signedIn}
            />
          </li>
        );
      })}
    </ul>
  );
}

function RivalCard({
  leagueId,
  you,
  row,
  locked,
  signedIn,
}: {
  leagueId: number;
  you: number;
  row: LeagueBoardRow;
  locked: boolean;
  signedIn: boolean;
}) {
  const odds = row.odds_vs_you!;
  const name = row.manager.player_name;
  const href = `/l/${leagueId}/vs/${row.manager.entry_id}?you=${you}`;

  const body = (
    <>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate font-semibold text-ink">
            You <span className="text-ink-faint">vs</span> {name}
          </h3>
          <p className="mt-0.5 truncate text-sm text-ink-dim">
            {row.manager.team_name}
          </p>
        </div>
        <Probability value={odds.p_above} size="md" />
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div>
          <dt className="text-xs text-ink-faint">Gap now</dt>
          <dd className="num mt-0.5 text-ink">{signedInt(odds.gap_now)}</dd>
        </div>
        <div>
          <dt className="text-xs text-ink-faint">Needed per GW</dt>
          <dd className="num mt-0.5 text-ink">
            {odds.gap_now < 0 ? `+${odds.points_per_gw_needed.toFixed(1)}` : "—"}
          </dd>
        </div>
      </dl>

      <p className="mt-4 text-sm leading-relaxed text-ink-dim">
        {varianceCopy(odds.variance)}
      </p>
    </>
  );

  if (!locked) {
    return (
      <Card
        as="article"
        className="h-full p-5 transition-colors hover:border-border-strong"
      >
        <Link href={href} className="block">
          {body}
          <span className="mt-4 inline-flex text-sm font-medium text-you">
            Open {name}&apos;s dossier →
          </span>
        </Link>
      </Card>
    );
  }

  return (
    <Card as="article" className="relative h-full overflow-hidden p-5">
      <div aria-hidden="true" className="pointer-events-none select-none blur-[5px]">
        {body}
      </div>
      <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-base/80 p-5 text-center">
        <p className="text-sm leading-relaxed text-ink">
          {signedIn
            ? `Your free dossier is used. Unlock ${name}'s and every other rival.`
            : `See exactly what it takes to catch ${name}.`}
        </p>
        <Link
          href={signedIn ? "/pricing" : `/signin?next=${encodeURIComponent(href)}`}
          className={cx(
            "inline-flex min-h-[44px] items-center justify-center rounded-[8px] px-4 py-2.5",
            "bg-you text-sm font-semibold text-[#06231a] transition-colors hover:bg-[#4ae8a5]",
          )}
        >
          Unlock {name}&apos;s dossier
        </Link>
        <p className="text-xs text-ink-faint">
          €4.99 a month, or €29.99 for the whole season
        </p>
      </div>
    </Card>
  );
}
