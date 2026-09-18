"use client";

import { useEffect } from "react";

import { track } from "@/lib/api";

const STORAGE_KEY = "overtake_first_touch";

/** Referrers worth a name of their own, and what kind of visit each one is. */
const KNOWN_SOURCES: [RegExp, string, string][] = [
  [/(^|\.)google\.[a-z.]+$/, "google", "organic"],
  [/(^|\.)bing\.com$/, "bing", "organic"],
  [/(^|\.)duckduckgo\.com$/, "duckduckgo", "organic"],
  [/(^|\.)reddit\.com$/, "reddit", "social"],
  [/(^|\.)(t\.co|x\.com|twitter\.com)$/, "x", "social"],
  [/(^|\.)facebook\.com$/, "facebook", "social"],
  [/(^|\.)instagram\.com$/, "instagram", "social"],
  [/(^|\.)tiktok\.com$/, "tiktok", "social"],
  [/(^|\.)discord(app)?\.com$/, "discord", "social"],
  [/(^|\.)youtube\.com$/, "youtube", "social"],
];

let recorded = false;

/**
 * Records where this browser first came from, once.
 *
 * The funnel counted conversions and said nothing about which post, community
 * or shared link brought anyone, so the weekly scorecard could not tell a
 * channel worth twenty minutes a day from one worth none. This sends the first
 * touch — utm_ tags when a link carries them, otherwise the referring site's
 * host, never its full address — to the same first-party, IP-free counter as
 * every other funnel event.
 */
export function Attribution() {
  useEffect(() => {
    if (recorded) return;
    recorded = true;
    try {
      if (window.localStorage.getItem(STORAGE_KEY)) return;
    } catch {
      // Storage refused: still count this visit, just without remembering it.
    }
    track("visit_started", firstTouch(window.location.href, document.referrer));
    try {
      window.localStorage.setItem(STORAGE_KEY, new Date().toISOString());
    } catch {
      /* A per-browser convenience; nothing depends on it being kept. */
    }
  }, []);
  return null;
}

function firstTouch(href: string, referrer: string): Record<string, string | null> {
  const url = new URL(href);
  const tag = (name: string) => url.searchParams.get(`utm_${name}`)?.slice(0, 80) || null;

  let referrerHost: string | null = null;
  try {
    const host = referrer ? new URL(referrer).hostname.replace(/^www\./, "") : "";
    // Moving between our own pages is not a source.
    if (host && host !== url.hostname.replace(/^www\./, "")) referrerHost = host;
  } catch {
    referrerHost = null;
  }

  const known = referrerHost
    ? KNOWN_SOURCES.find(([pattern]) => pattern.test(referrerHost as string))
    : undefined;

  return {
    source: tag("source") ?? known?.[1] ?? referrerHost ?? "direct",
    medium: tag("medium") ?? known?.[2] ?? (referrerHost ? "referral" : "direct"),
    campaign: tag("campaign"),
    referrer_host: referrerHost,
    // The path only: a query string can carry anything, including someone's email.
    landing: url.pathname.slice(0, 120),
  };
}
