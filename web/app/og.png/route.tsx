import { ImageResponse } from "next/og";

import { DEFAULT_OG_IMAGE } from "@/lib/site";

/**
 * The default share card at /og.png, for every page without one of its own.
 *
 * The site declared `summary_large_image` everywhere and shipped no image, so
 * a shared homepage, pricing page or player page unfurled as a bare link. Built
 * once at build time from the same palette as the league cards; it needs no
 * data, so it can never fail on an API outage.
 */
export const dynamic = "force-static";

export function GET() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          background: "#0B0F14",
          color: "#E8EDF4",
          padding: 72,
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ fontSize: 28, fontWeight: 800, letterSpacing: -0.5 }}>OVERTAKE</div>
        <div style={{ fontSize: 64, fontWeight: 800, marginTop: 22, letterSpacing: -2 }}>
          Stop trying to beat millions of strangers.
        </div>
        <div style={{ fontSize: 38, marginTop: 14, color: "#3DDC97" }}>
          Start beating the eight people in your league.
        </div>
        <div style={{ fontSize: 24, marginTop: 40, color: "#7C8CA1" }}>
          Your odds against every rival in your FPL mini-league · 20,000 simulated seasons
        </div>
      </div>
    ),
    {
      width: DEFAULT_OG_IMAGE.width,
      height: DEFAULT_OG_IMAGE.height,
      headers: { "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800" },
    },
  );
}
