"use client";

import { useState } from "react";

import { Button } from "@/components/ui";
import { track } from "@/lib/api";

/**
 * The growth loop. The shared artefact is *about the recipient* — "you are 71%
 * to finish above me" is a claim about them, in a group where they have social
 * standing to defend. So sharing is one tap with a pre-written message, and
 * there are no referral bribes: a bribed share is a worse share.
 */
export function ShareButton({
  leagueId,
  leagueName,
  entryId,
  rivalName,
  probability,
  variant = "secondary",
}: {
  leagueId: number;
  leagueName: string;
  entryId: number | null;
  rivalName?: string;
  probability?: number;
  variant?: "primary" | "secondary";
}) {
  const [copied, setCopied] = useState(false);

  const url =
    typeof window === "undefined"
      ? ""
      : `${window.location.origin}/l/${leagueId}${entryId ? `?entry=${entryId}` : ""}`;

  const text =
    rivalName && probability !== undefined
      ? `I'm ${Math.round(probability * 100)}% to finish above ${rivalName} in ${leagueName}.`
      : `Here's what it takes to win ${leagueName} from here.`;

  async function share() {
    track("share_clicked", { league_id: leagueId, has_rival: Boolean(rivalName) });
    const payload = { title: "Overtake", text, url };

    if (typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share(payload);
        return;
      } catch {
        // The user dismissed the sheet, or the browser refused. Fall back.
      }
    }
    try {
      await navigator.clipboard.writeText(`${text}\n${url}`);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2500);
    } catch {
      window.prompt("Copy this link", `${text}\n${url}`);
    }
  }

  return (
    <Button variant={variant} onClick={share} aria-live="polite">
      {copied ? "Copied ✓" : "Share to chat"}
    </Button>
  );
}
