/**
 * Formatting rules from 09-ux-ui-spec.md, in one place so they cannot drift.
 *
 * Probabilities to a whole percent. Points to one decimal. Every gain or loss
 * carries a sign or an arrow as well as a colour, because meaning is never
 * encoded in colour alone.
 */

export function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function pctDelta(value: number): string {
  const points = value * 100;
  const sign = points > 0 ? "+" : points < 0 ? "−" : "";
  return `${sign}${Math.abs(points).toFixed(1)}pp`;
}

export function points(value: number, decimals = 1): string {
  return value.toFixed(decimals);
}

export function signedPoints(value: number, decimals = 1): string {
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}${Math.abs(value).toFixed(decimals)}`;
}

export function signedInt(value: number): string {
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}${Math.abs(value)}`;
}

export function money(value: number): string {
  return `£${value.toFixed(1)}m`;
}

export function ordinal(n: number): string {
  const rest = n % 100;
  if (rest >= 11 && rest <= 13) return `${n}th`;
  switch (n % 10) {
    case 1:
      return `${n}st`;
    case 2:
      return `${n}nd`;
    case 3:
      return `${n}rd`;
    default:
      return `${n}th`;
  }
}

/** "2d 04:11" — the countdown format used in the header and the dossier. */
export function countdown(msRemaining: number): string {
  if (msRemaining <= 0) return "Deadline passed";
  const totalSeconds = Math.floor(msRemaining / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const clock = `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(
    seconds,
  ).padStart(2, "0")}`;
  return days > 0 ? `${days}d ${clock}` : clock;
}

/** A screen-reader friendly version of the countdown. */
export function countdownLabel(msRemaining: number): string {
  if (msRemaining <= 0) return "The deadline has passed";
  const totalMinutes = Math.floor(msRemaining / 60000);
  const days = Math.floor(totalMinutes / 1440);
  const hours = Math.floor((totalMinutes % 1440) / 60);
  const minutes = totalMinutes % 60;
  const parts: string[] = [];
  if (days) parts.push(`${days} day${days === 1 ? "" : "s"}`);
  if (hours) parts.push(`${hours} hour${hours === 1 ? "" : "s"}`);
  if (!days) parts.push(`${minutes} minute${minutes === 1 ? "" : "s"}`);
  return `${parts.join(", ")} until the deadline`;
}

export function timestamp(iso: string | null | undefined): string {
  if (!iso) return "unknown";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "unknown";
  return date.toLocaleString("en-GB", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  });
}

export function shortDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

/**
 * Accepts a league URL or a bare id, because people paste the URL from the FPL
 * site far more often than they know what a league id is.
 */
export function parseLeagueId(input: string): number | null {
  const trimmed = input.trim();
  if (!trimmed) return null;

  const patterns = [
    /leagues\/(\d+)\/standings/i,
    /leagues-classic\/(\d+)/i,
    /league\/(\d+)/i,
    /^(\d+)$/,
  ];
  for (const pattern of patterns) {
    const match = trimmed.match(pattern);
    const captured = match?.[1];
    if (captured) {
      const id = Number.parseInt(captured, 10);
      if (Number.isSafeInteger(id) && id > 0) return id;
    }
  }

  const digits = trimmed.match(/(\d{2,})/);
  if (digits?.[1]) {
    const id = Number.parseInt(digits[1], 10);
    if (Number.isSafeInteger(id) && id > 0) return id;
  }
  return null;
}

/** Accepts an FPL entry URL or a bare manager id. */
export function parseEntryId(input: string): number | null {
  const trimmed = input.trim();
  if (!trimmed) return null;
  const match = trimmed.match(/entry\/(\d+)/i) ?? trimmed.match(/^(\d+)$/);
  const captured = match?.[1];
  if (!captured) return null;
  const id = Number.parseInt(captured, 10);
  return Number.isSafeInteger(id) && id > 0 ? id : null;
}

/** Colour class for a probability. Always paired with a number, never alone. */
export function oddsTone(p: number): string {
  if (p >= 0.6) return "text-you";
  if (p <= 0.25) return "text-rival";
  return "text-ink";
}

export function varianceCopy(variance: string): string {
  switch (variance) {
    case "seek":
      return "Take risks they are not taking";
    case "suppress":
      return "Cover their picks, do not chase";
    default:
      return "Too close to call either way";
  }
}
