import { ImageResponse } from "next/og";

import { serverFetchOrNull } from "@/lib/api";
import type { LeagueBoard } from "@/lib/types";

export const alt = "Overtake league odds";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

/**
 * The league odds card — half of the growth loop.
 *
 * It carries the rivals' real team names on purpose: the shared artefact is a
 * claim about the recipient, in a group where they have standing to defend.
 * That is what makes it get opened, and it has to look good enough to post
 * without embarrassment. That is a design requirement, not a nice-to-have.
 */
export default async function LeagueOgImage({
  params,
}: {
  params: { leagueId: string };
}) {
  const board = await serverFetchOrNull<LeagueBoard>(`/leagues/${params.leagueId}`);

  if (!board) {
    return new ImageResponse(<Fallback />, size);
  }

  const rows = board.rows.slice(0, 8);

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
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ fontSize: 26, fontWeight: 800, letterSpacing: -0.5 }}>
            OVERTAKE
          </div>
          <div style={{ fontSize: 22, color: "#7C8CA1" }}>
            Gameweek {board.gameweek}
          </div>
        </div>

        <div
          style={{
            fontSize: 54,
            fontWeight: 800,
            marginTop: 18,
            letterSpacing: -1.5,
            maxWidth: 1000,
            overflow: "hidden",
          }}
        >
          {board.league.name}
        </div>

        <div style={{ display: "flex", flexDirection: "column", marginTop: 28, gap: 6 }}>
          {rows.map((row, index) => (
            <div
              key={row.manager.entry_id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 18,
                padding: "10px 18px",
                borderRadius: 8,
                background: row.is_you ? "#0F1F19" : "#121821",
                border: `1px solid ${row.is_you ? "#1D6F4E" : "#1C2531"}`,
              }}
            >
              <div style={{ width: 34, fontSize: 24, color: "#7C8CA1" }}>
                {index + 1}
              </div>
              <div
                style={{
                  flex: 1,
                  fontSize: 27,
                  fontWeight: 600,
                  color: row.is_you ? "#3DDC97" : "#E8EDF4",
                  overflow: "hidden",
                }}
              >
                {row.manager.team_name}
              </div>
              <div style={{ fontSize: 24, color: "#93A1B4", width: 90, textAlign: "right" }}>
                {row.manager.total}
              </div>
              <div
                style={{
                  fontSize: 30,
                  fontWeight: 700,
                  width: 110,
                  textAlign: "right",
                  color: row.odds_vs_you
                    ? row.odds_vs_you.p_above >= 0.5
                      ? "#3DDC97"
                      : "#FF6B6B"
                    : "#7C8CA1",
                }}
              >
                {row.odds_vs_you
                  ? `${Math.round(row.odds_vs_you.p_above * 100)}%`
                  : `${Math.round(row.p_win * 100)}%`}
              </div>
            </div>
          ))}
        </div>

        <div
          style={{
            display: "flex",
            marginTop: "auto",
            paddingTop: 20,
            fontSize: 20,
            color: "#7C8CA1",
          }}
        >
          {board.you
            ? "Probability you finish above each of them"
            : "Probability each of them wins the league"}
          {" · simulated "}
          {board.provenance.n_sims.toLocaleString("en-GB")}
          {" seasons"}
        </div>
      </div>
    ),
    size,
  );
}

function Fallback() {
  return (
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
      <div style={{ fontSize: 58, fontWeight: 800, marginTop: 16, letterSpacing: -2 }}>
        Stop trying to beat 13 million strangers.
      </div>
      <div style={{ fontSize: 34, marginTop: 12, color: "#3DDC97" }}>
        Start beating the eight people in your league.
      </div>
    </div>
  );
}
