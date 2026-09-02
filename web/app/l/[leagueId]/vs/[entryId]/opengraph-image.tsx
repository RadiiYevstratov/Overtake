import { ImageResponse } from "next/og";

import { serverFetchOrNull } from "@/lib/api";
import type { Dossier } from "@/lib/types";

export const alt = "Overtake head-to-head odds";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

/**
 * The head-to-head card: "I'm 71% to finish above you."
 *
 * This is the sentence someone sends into a group chat unprompted, and every
 * recipient is a qualified lead who is about to check what it says about them.
 */
export default async function DossierOgImage({
  params,
  searchParams,
}: {
  params: { leagueId: string; entryId: string };
  searchParams?: { you?: string };
}) {
  const you = searchParams?.you;
  const dossier = you
    ? await serverFetchOrNull<Dossier>(
        `/leagues/${params.leagueId}/rivals/${params.entryId}/dossier?you=${you}`,
      )
    : null;

  if (!dossier) {
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
            padding: 64,
            fontFamily: "sans-serif",
          }}
        >
          <div style={{ fontSize: 26, fontWeight: 800 }}>OVERTAKE</div>
          <div style={{ fontSize: 56, fontWeight: 800, marginTop: 18, letterSpacing: -2 }}>
            What does it take to catch them?
          </div>
        </div>
      ),
      size,
    );
  }

  const percent = Math.round(dossier.odds.p_above * 100);
  const behind = dossier.odds.gap_now < 0;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          background: "#0B0F14",
          color: "#E8EDF4",
          padding: "56px 64px",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ fontSize: 26, fontWeight: 800, letterSpacing: -0.5 }}>OVERTAKE</div>

        <div style={{ display: "flex", alignItems: "center", gap: 22, marginTop: 34 }}>
          <div style={{ fontSize: 44, fontWeight: 800, color: "#3DDC97" }}>
            {dossier.you.team_name}
          </div>
          <div style={{ fontSize: 32, color: "#7C8CA1" }}>vs</div>
          <div style={{ fontSize: 44, fontWeight: 800, color: "#FF6B6B" }}>
            {dossier.rival.team_name}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "baseline", gap: 22, marginTop: 40 }}>
          <div
            style={{
              fontSize: 168,
              fontWeight: 800,
              letterSpacing: -6,
              color: percent >= 50 ? "#3DDC97" : "#FF6B6B",
              lineHeight: 1,
            }}
          >
            {percent}%
          </div>
          <div style={{ fontSize: 34, color: "#93A1B4", maxWidth: 460 }}>
            to finish above {dossier.rival.player_name}
          </div>
        </div>

        <div style={{ display: "flex", gap: 48, marginTop: 40 }}>
          <Stat
            value={`${Math.abs(dossier.odds.gap_now)}`}
            label={behind ? "points behind" : "points ahead"}
          />
          <Stat value={`${dossier.gameweeks_left}`} label="gameweeks left" />
          {behind ? (
            <Stat
              value={`+${dossier.odds.points_per_gw_needed.toFixed(1)}`}
              label="needed per gameweek"
            />
          ) : null}
        </div>

        <div
          style={{
            display: "flex",
            marginTop: "auto",
            fontSize: 20,
            color: "#7C8CA1",
          }}
        >
          {dossier.league.name} · simulated{" "}
          {dossier.provenance.n_sims.toLocaleString("en-GB")} seasons
        </div>
      </div>
    ),
    size,
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column" }}>
      <div style={{ fontSize: 52, fontWeight: 700 }}>{value}</div>
      <div style={{ fontSize: 20, color: "#7C8CA1", marginTop: 4 }}>{label}</div>
    </div>
  );
}
