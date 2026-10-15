"use client";

import { useState } from "react";

import { Button } from "@/components/ui";
import { track } from "@/lib/api";
import { shareOrCopy, shareUrl } from "@/lib/share";

/**
 * The growth loop. The shared artefact is *about the recipient* — "you are 71%
 * to finish above me" is a claim about them, in a group where they have social
 * standing to defend. So sharing is one tap with a pre-written message, and
 * there are no referral bribes: a bribed share is a worse share.
 *
 * The link names nobody: see `shareUrl`.
 */
export function ShareButton({
  leagueId,
  leagueName,
  rivalName,
  probability,
  variant = "secondary",
}: {
  leagueId: number;
  leagueName: string;
  rivalName?: string;
  probability?: number;
  variant?: "primary" | "secondary";
}) {
  const [copied, setCopied] = useState(false);

  const text =
    rivalName && probability !== undefined
      ? `I'm ${Math.round(probability * 100)}% to finish above ${rivalName} in ${leagueName}.`
      : `Here's what it takes to win ${leagueName} from here.`;

  async function share() {
    track("share_clicked", { league_id: leagueId, has_rival: Boolean(rivalName) });
    const outcome = await shareOrCopy(
      // Tagged, so a friend who opens it is counted as arriving by a share —
      // the growth loop's own line in the scorecard.
      { title: "Overtake", text, url: shareUrl(window.location.origin, leagueId) },
      {
        share:
          typeof navigator.share === "function"
            ? (data) => navigator.share(data)
            : undefined,
        writeText: navigator.clipboard?.writeText
          ? (value) => navigator.clipboard.writeText(value)
          : undefined,
        prompt: (message, value) => window.prompt(message, value),
      },
    );
    if (outcome === "copied") {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2500);
    }
  }

  return (
    <Button variant={variant} onClick={share} aria-live="polite">
      {copied ? "Copied ✓" : "Share to chat"}
    </Button>
  );
}
