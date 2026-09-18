"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

/**
 * Re-renders the page every few seconds until the server has something new.
 *
 * A league's first visit answers "still reading" while its squads are fetched
 * from FPL, and the page used to leave it there — a visitor saw "Simulating…"
 * until they thought to reload. This asks again on their behalf, and when the
 * board is ready the page renders it and this component is gone with the rest
 * of the waiting state.
 *
 * It gives up after a couple of minutes, because an FPL outage would otherwise
 * keep a tab polling for ever. Then it says so, plainly, and offers the button.
 */
export function AutoRefresh({
  everyMs = 3000,
  maxTries = 40,
}: {
  everyMs?: number;
  maxTries?: number;
}) {
  const router = useRouter();
  const [tries, setTries] = useState(0);

  useEffect(() => {
    if (tries >= maxTries) return;
    const timer = setTimeout(() => {
      router.refresh();
      setTries((n) => n + 1);
    }, everyMs);
    return () => clearTimeout(timer);
  }, [tries, maxTries, everyMs, router]);

  if (tries < maxTries) return null;
  return (
    <p role="status" className="mt-4 text-center text-sm text-ink-dim">
      This is taking longer than it should — the FPL site may be slow right now.{" "}
      <button
        type="button"
        onClick={() => {
          setTries(0);
          router.refresh();
        }}
        className="text-you underline"
      >
        Try again
      </button>
    </p>
  );
}
