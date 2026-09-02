"use client";

import { useEffect, useRef } from "react";

import { track } from "@/lib/api";

/**
 * The `aha_reached` event: the visitor has scrolled past "WHERE THE GAP IS".
 *
 * This is metric #1 in the GO/NO-GO table, and the whole 14-day plan is written
 * against it — so it is measured where the value actually lands, not on page
 * load. Fires once per page view.
 */
export function AhaTracker({
  leagueId,
  rivalId,
}: {
  leagueId: number;
  rivalId: number;
}) {
  const sentinel = useRef<HTMLDivElement>(null);
  const fired = useRef(false);

  useEffect(() => {
    const node = sentinel.current;
    if (!node || fired.current) return;

    if (typeof IntersectionObserver === "undefined") {
      fired.current = true;
      track("aha_reached", { league_id: leagueId, rival: rivalId });
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting && !fired.current) {
            fired.current = true;
            track("aha_reached", { league_id: leagueId, rival: rivalId });
            observer.disconnect();
          }
        }
      },
      { threshold: 0.6 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [leagueId, rivalId]);

  return <div ref={sentinel} aria-hidden="true" className="h-px" />;
}
