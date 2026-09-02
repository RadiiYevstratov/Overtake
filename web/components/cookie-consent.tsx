"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const STORAGE_KEY = "overtake_consent";

/**
 * Essential-only by default (11-legal-security-risk.md §1.4).
 *
 * Nothing non-essential loads before an explicit accept, and declining is
 * exactly as easy as accepting — one button each, same size, no dark pattern.
 * Funnel counting continues server-side and cookielessly either way, which is
 * why declining costs the product nothing.
 */
export function CookieConsent() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    try {
      if (!window.localStorage.getItem(STORAGE_KEY)) setVisible(true);
    } catch {
      // A browser blocking storage is itself a decline. Respect it silently.
    }
  }, []);

  function decide(choice: "accepted" | "declined") {
    try {
      window.localStorage.setItem(STORAGE_KEY, choice);
    } catch {
      /* Nothing to do; the banner simply reappears next visit. */
    }
    setVisible(false);
  }

  if (!visible) return null;

  return (
    <div
      role="dialog"
      aria-modal="false"
      aria-labelledby="consent-title"
      className="fixed inset-x-0 bottom-0 z-50 border-t border-border bg-surface/98 backdrop-blur"
    >
      <div className="mx-auto flex max-w-4xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:px-6">
        <div className="flex-1">
          <h2 id="consent-title" className="text-sm font-semibold text-ink">
            Analytics cookies?
          </h2>
          <p className="mt-1 text-sm leading-relaxed text-ink-dim">
            Overtake works fully without them. If you say yes, we use them to see which
            parts of the product actually help.{" "}
            <Link href="/cookies" className="underline hover:text-ink">
              What we collect
            </Link>
            .
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => decide("declined")}
            className="min-h-[44px] flex-1 rounded-[8px] border border-border-strong px-4 py-2.5 text-sm transition-colors hover:border-ink-faint sm:flex-none"
          >
            No thanks
          </button>
          <button
            onClick={() => decide("accepted")}
            className="min-h-[44px] flex-1 rounded-[8px] border border-border-strong px-4 py-2.5 text-sm transition-colors hover:border-ink-faint sm:flex-none"
          >
            Allow
          </button>
        </div>
      </div>
    </div>
  );
}
