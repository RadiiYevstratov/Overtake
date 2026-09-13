import type { LeagueBoardRow, Me } from "@/lib/types";

/**
 * What a viewer can open in full, mirroring the API's rule so the rival cards
 * and the picker never promise more than the dossier page will show. The API
 * is what enforces it; this only keeps the labels honest.
 */
export interface DossierAccess {
  signedIn: boolean;
  isPro: boolean;
  /** Entry ids in this league that this free account has chosen to see in full. */
  freeRivals: number[];
  /** A free account that has not used its rival for the season yet. */
  canChoose: boolean;
}

export function dossierAccess(me: Me | null, leagueId: number): DossierAccess {
  if (!me) return { signedIn: false, isPro: false, freeRivals: [], canChoose: false };
  const chosen = me.free_rivals ?? [];
  const allowance = me.limits.dossiers_per_season;
  return {
    signedIn: true,
    isPro: me.plan.is_pro,
    freeRivals: chosen.filter((r) => r.league_id === leagueId).map((r) => r.entry_id),
    canChoose: !me.plan.is_pro && (allowance === null || chosen.length < allowance),
  };
}

/** Rivals a signed-in free account could only open in full with Pro. */
export function proOnlyRivals(access: DossierAccess, rows: LeagueBoardRow[]): number[] {
  if (!access.signedIn || access.isPro || access.canChoose) return [];
  return rows
    .map((row) => row.manager.entry_id)
    .filter((entry) => !access.freeRivals.includes(entry));
}
