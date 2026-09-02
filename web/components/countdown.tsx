"use client";

import { useEffect, useState } from "react";

import { countdown, countdownLabel } from "@/lib/format";

/**
 * The persistent deadline clock.
 *
 * Rendered as a static value first and hydrated on the client, so it never
 * causes a server/client mismatch and never blocks the first paint.
 */
export function Countdown({
  deadline,
  gameweek,
  size = "pill",
}: {
  deadline: string;
  gameweek?: number | null;
  size?: "pill" | "large";
}) {
  const target = new Date(deadline).getTime();
  const [remaining, setRemaining] = useState<number | null>(null);

  useEffect(() => {
    const tick = () => setRemaining(target - Date.now());
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [target]);

  const passed = remaining !== null && remaining <= 0;

  if (size === "large") {
    return (
      <div>
        <div
          className={`num text-3xl font-semibold ${passed ? "text-ink-faint" : "text-ink"}`}
          aria-hidden="true"
        >
          {remaining === null ? "—" : countdown(remaining)}
        </div>
        <span className="sr-only">
          {remaining === null ? "Loading the countdown" : countdownLabel(remaining)}
        </span>
        <div className="mt-1 text-xs text-ink-faint">
          {gameweek ? `Gameweek ${gameweek} deadline` : "Next deadline"}
        </div>
      </div>
    );
  }

  return (
    <div
      className="hidden items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 sm:inline-flex"
      title={gameweek ? `Gameweek ${gameweek} deadline` : "Next deadline"}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${passed ? "bg-ink-faint" : "bg-you"}`}
        aria-hidden="true"
      />
      <span className="text-[11px] uppercase tracking-wider text-ink-faint">
        {gameweek ? `GW${gameweek}` : "Next"}
      </span>
      <span className="num text-sm text-ink" aria-hidden="true">
        {remaining === null ? "—" : countdown(remaining)}
      </span>
      <span className="sr-only">
        {remaining === null ? "Loading the countdown" : countdownLabel(remaining)}
      </span>
    </div>
  );
}
