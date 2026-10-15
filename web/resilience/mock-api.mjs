/**
 * A scriptable stand-in for the Overtake API, for the resilience tests.
 *
 * Serves just enough of the public routes for the SEO pages to render, records
 * every call, and can be told to fail any path in any way — a status, a
 * Retry-After, a dropped connection — through POST /__control.
 */
import http from "node:http";

const PORT = Number(process.env.MOCK_API_PORT ?? 8765);

const PLAYERS = {
  "phil-foden": { id: 398, name: "Foden", full: "Phil Foden", position: "MID", price: 6.8 },
  "bukayo-saka": { id: 12, name: "Saka", full: "Bukayo Saka", position: "MID", price: 9.6 },
  "cole-palmer": { id: 300, name: "Palmer", full: "Cole Palmer", position: "MID", price: 9.7 },
  "erling-haaland": { id: 411, name: "Haaland", full: "Erling Haaland", position: "FWD", price: 15.6 },
};

let overrides = {};
let calls = [];

function playerPage(slug) {
  const p = PLAYERS[slug];
  const peers = Object.entries(PLAYERS)
    .filter(([other, q]) => other !== slug && q.position === p.position)
    .map(([other, q]) => ({ slug: other, name: q.name, price: q.price }));
  return {
    player: {
      id: p.id,
      slug,
      name: p.name,
      full_name: p.full,
      team: "Man City",
      team_short: "MCI",
      team_slug: "man-city",
      position: p.position,
      price: p.price,
      status: "a",
      news: null,
      selected_by_percent: 12.5,
      total_points: 40,
      minutes: 500,
      is_set_piece_taker: false,
    },
    projection: {
      horizon: [7, 8],
      per_gameweek: [
        { gameweek: 7, mu: 5.1, p_start: 0.9 },
        { gameweek: 8, mu: 4.8, p_start: 0.9 },
      ],
      expected_points_next_6: 9.9,
      start_probability: 0.9,
    },
    history: [{ gameweek: 6, points: 6, minutes: 90, goals: 1, assists: 0, bonus: 1 }],
    fixtures: [
      { gameweek: 7, opponent: "IPS", is_home: true, difficulty: 2, kickoff_utc: "2026-10-17T14:00:00Z" },
    ],
    comparisons: peers,
    accuracy: { mae: 1.19, gameweeks: 5, model_version: "proj-1" },
  };
}

function route(path) {
  if (path === "/api/v1/meta/season") {
    return [200, {
      season: "2026/27",
      current_gameweek: 6,
      next_gameweek: 7,
      next_deadline_utc: "2030-10-17T10:00:00Z",
      players_tracked: 4,
      fpl_managers: 11_000_000,
      accuracy: { mae: 1.19, gameweeks: 5, model_version: "proj-1" },
      simulations: { n_sims: 20000, seed: 8814 },
    }];
  }
  if (path === "/api/v1/billing/offer") return [200, { active: false, code: null }];
  if (path.startsWith("/api/v1/players?")) {
    return [200, {
      players: Object.entries(PLAYERS).map(([slug, p]) => ({
        id: p.id, slug, name: p.name, team_short: "MCI", position: p.position,
        price: p.price, total_points: 40, selected_by_percent: 12.5,
      })),
    }];
  }
  const player = path.match(/^\/api\/v1\/players\/([a-z0-9-]+)$/);
  if (player) {
    return PLAYERS[player[1]]
      ? [200, playerPage(player[1])]
      : [404, { error: { code: "NOT_FOUND", message: "We do not have a page for that player." } }];
  }
  return [404, { error: { code: "NOT_FOUND", message: "Not mocked." } }];
}

function send(res, status, body, headers = {}) {
  res.writeHead(status, { "content-type": "application/json", ...headers });
  res.end(JSON.stringify(body));
}

const server = http.createServer((req, res) => {
  const url = req.url ?? "/";
  if (url === "/__control" && req.method === "POST") {
    let raw = "";
    req.on("data", (chunk) => (raw += chunk));
    req.on("end", () => {
      const body = JSON.parse(raw || "{}");
      if (body.reset) {
        overrides = {};
        calls = [];
      }
      Object.assign(overrides, body.routes ?? {});
      if (body.add) PLAYERS[body.add.slug] = body.add.player;
      send(res, 200, { ok: true });
    });
    return;
  }
  if (url === "/__calls") return send(res, 200, calls);

  calls.push({ path: url, clientIp: req.headers["x-overtake-client-ip"] ?? null, cookie: req.headers.cookie ?? null });
  // An override applies to every call, or to the next `times` calls only.
  const override = overrides[url];
  if (override && (override.times === undefined || override.times > 0)) {
    if (override.times !== undefined) override.times -= 1;
    if (override.drop) return req.socket.destroy();
    const headers = override.retryAfter ? { "Retry-After": String(override.retryAfter) } : {};
    const body = override.body ?? { error: { code: "MOCKED", message: "Mocked failure." } };
    return send(res, override.status, body, headers);
  }
  const [status, body] = route(url);
  send(res, status, body);
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`mock api on ${PORT}`);
});
