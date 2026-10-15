/**
 * The share link and the share action, kept free of React so they can be
 * tested on their own.
 */

/**
 * A link to a league board, tagged as a share.
 *
 * It never names a manager. It used to carry the sharer's `entry`, which made
 * every recipient arrive as the sharer — their row marked "you", their odds
 * presented as the reader's own. The recipient picks their own name, or their
 * account decides; the message text says who sent it.
 */
export function shareUrl(origin: string, leagueId: number): string {
  const params = new URLSearchParams({ utm_source: "share", utm_medium: "link" });
  return `${origin}/l/${leagueId}?${params.toString()}`;
}

export type ShareOutcome = "shared" | "cancelled" | "copied" | "prompted";

export interface ShareEnvironment {
  share?: (data: { title: string; text: string; url: string }) => Promise<void>;
  writeText?: (text: string) => Promise<void>;
  prompt: (message: string, value: string) => void;
}

/**
 * The platform's share sheet when there is one; the clipboard only when there
 * is not, or the platform refuses the data outright.
 *
 * Dismissing the sheet is a decision, not an error: it used to fall through to
 * the clipboard, so cancelling a share quietly overwrote whatever the person
 * had copied.
 */
export async function shareOrCopy(
  payload: { title: string; text: string; url: string },
  env: ShareEnvironment,
): Promise<ShareOutcome> {
  if (env.share) {
    try {
      await env.share(payload);
      return "shared";
    } catch (error) {
      if (isAbort(error)) return "cancelled";
      // Not a cancellation — the platform could not share this. Fall back.
    }
  }
  const combined = `${payload.text}\n${payload.url}`;
  if (env.writeText) {
    try {
      await env.writeText(combined);
      return "copied";
    } catch {
      // Clipboard refused (permissions, insecure context). Offer it to copy by hand.
    }
  }
  env.prompt("Copy this link", combined);
  return "prompted";
}

function isAbort(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "name" in error &&
    (error as { name: unknown }).name === "AbortError"
  );
}
