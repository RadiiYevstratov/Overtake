"use client";

import { useEffect, useState } from "react";

import { Button, Card } from "@/components/ui";
import { INTERNAL_KEY } from "@/lib/api";

/**
 * Marks this browser as ours, so the scorecard ignores everything it does.
 *
 * Signing in already excludes an admin's browser, but most testing happens
 * signed out — a phone, a private window, a shared link opened to check it
 * still works. Those visits looked exactly like a stranger's and moved every
 * rate on the page that decides whether the product works.
 */
export default function InternalPage() {
  const [marked, setMarked] = useState<boolean | null>(null);

  useEffect(() => {
    try {
      setMarked(window.localStorage.getItem(INTERNAL_KEY) === "1");
    } catch {
      setMarked(false);
    }
  }, []);

  function set(on: boolean) {
    try {
      if (on) window.localStorage.setItem(INTERNAL_KEY, "1");
      else window.localStorage.removeItem(INTERNAL_KEY);
      setMarked(on);
    } catch {
      setMarked(null);
    }
  }

  return (
    <div className="mx-auto max-w-xl px-4 py-16 sm:px-6">
      <h1 className="text-3xl font-bold tracking-tight">This browser</h1>
      <p className="mt-2 text-ink-dim">
        Mark it as yours and nothing it does will count on the scorecard. It
        applies to this browser on this device only, and it survives sign-out.
      </p>

      <Card className="mt-8 p-6">
        <p className="text-sm">
          Status:{" "}
          {marked === null ? (
            <span className="text-ink-faint">checking…</span>
          ) : marked ? (
            <span className="font-semibold text-you">
              yours — events from here are hidden
            </span>
          ) : (
            <span className="font-semibold text-warn">
              counted as an ordinary visitor
            </span>
          )}
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Button onClick={() => set(true)} disabled={marked === true}>
            Mark as mine
          </Button>
          <Button variant="secondary" onClick={() => set(false)} disabled={marked === false}>
            Count it normally
          </Button>
        </div>
        <p className="mt-5 text-xs leading-relaxed text-ink-faint">
          Hidden events are never deleted. The scorecard at /app/funnel says how
          many it is leaving out, and can show them again.
        </p>
      </Card>
    </div>
  );
}
