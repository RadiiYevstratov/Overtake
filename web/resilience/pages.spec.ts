import { expect, test, type APIRequestContext } from "@playwright/test";

/**
 * What the public pages answer when the API misbehaves. The bug these guard:
 * a rate limit mid-crawl turned live player pages into 404s, which tells a
 * search engine the page is gone.
 */

const API = "http://127.0.0.1:8765";

async function control(request: APIRequestContext, body: unknown) {
  const response = await request.post(`${API}/__control`, { data: body });
  expect(response.ok()).toBe(true);
}

async function callsTo(request: APIRequestContext, path: string) {
  const calls = (await (await request.get(`${API}/__calls`)).json()) as {
    path: string;
    clientIp: string | null;
    cookie: string | null;
  }[];
  return calls.filter((call) => call.path === path);
}

let counter = 0;
/** A player only this test knows about, so no other test's cache can serve it. */
async function freshPlayer(request: APIRequestContext) {
  counter += 1;
  const slug = `test-player-${Date.now()}-${counter}`;
  await control(request, {
    add: { slug, player: { id: 5000 + counter, name: `Tester${counter}`, full: `Test Player ${counter}`, position: "MID", price: 7.0 } },
  });
  return slug;
}

test.beforeEach(async ({ request }) => {
  await control(request, { reset: true });
});

test("an existing player renders, with comparison links from the same response", async ({
  request,
}) => {
  const slug = await freshPlayer(request);
  const response = await request.get(`/player/${slug}`);
  expect(response.status()).toBe(200);
  const html = await response.text();
  expect(html).toContain(`Test Player`);
  expect(html).toMatch(/href="\/compare\/[a-z0-9-]+-vs-[a-z0-9-]+"/);
  // Breadcrumb JSON-LD points at a page that exists, with absolute URLs.
  expect(html).toContain('"item":"https://overtakefpl.example/players"');
});

test("a player FPL does not have is a real 404", async ({ request }) => {
  const response = await request.get("/player/nobody-at-all");
  expect(response.status()).toBe(404);
});

test("a rate limit is a temporary error, never a 404", async ({ request, page }) => {
  const slug = await freshPlayer(request);
  await control(request, {
    routes: { [`/api/v1/players/${slug}`]: { status: 429, retryAfter: 60 } },
  });
  const response = await request.get(`/player/${slug}`);
  expect(response.status()).toBe(500);
  // An error page is never indexed in place of the player.
  expect(await response.text()).toContain('<meta name="robots" content="noindex"/>');

  // What a visitor sees: "try again", not "this player does not exist".
  const visit = await page.goto(`/player/${slug}`);
  expect(visit?.status()).toBe(500);
  await expect(page.getByRole("heading", { name: "Something went wrong" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Nothing here", exact: true })).toHaveCount(0);
});

test("a failing API is a temporary error, never a 404", async ({ request }) => {
  const slug = await freshPlayer(request);
  await control(request, { routes: { [`/api/v1/players/${slug}`]: { status: 503 } } });
  expect((await request.get(`/player/${slug}`)).status()).toBe(500);
});

test("an unreachable API is a temporary error, never a 404", async ({ request }) => {
  const slug = await freshPlayer(request);
  await control(request, { routes: { [`/api/v1/players/${slug}`]: { drop: true } } });
  expect((await request.get(`/player/${slug}`)).status()).toBe(500);
});

test("a short rate limit is waited out once and the page renders", async ({ request }) => {
  const slug = await freshPlayer(request);
  await control(request, {
    routes: { [`/api/v1/players/${slug}`]: { status: 429, retryAfter: 1, times: 1 } },
  });
  expect((await request.get(`/player/${slug}`)).status()).toBe(200);
  expect(await callsTo(request, `/api/v1/players/${slug}`)).toHaveLength(2);
});

test("the page recovers on the next request once the API does", async ({ request }) => {
  const slug = await freshPlayer(request);
  await control(request, { routes: { [`/api/v1/players/${slug}`]: { status: 503, times: 2 } } });
  expect((await request.get(`/player/${slug}`)).status()).toBe(500);
  // Nothing was cached from the failure — not a 404, not an empty page.
  expect((await request.get(`/player/${slug}`)).status()).toBe(200);
});

test("a cached page survives the API failing", async ({ request }) => {
  const slug = await freshPlayer(request);
  expect((await request.get(`/player/${slug}`)).status()).toBe(200);
  await control(request, { routes: { [`/api/v1/players/${slug}`]: { status: 503 } } });
  const response = await request.get(`/player/${slug}`);
  expect(response.status()).toBe(200);
  expect(await response.text()).toContain("Test Player");
});

test("the cache is shared between visitors, and a miss is charged to the visitor", async ({
  request,
}) => {
  const slug = await freshPlayer(request);
  const first = await request.get(`/player/${slug}`, {
    headers: { "fly-client-ip": "203.0.113.1", cookie: "overtake_consent=1" },
  });
  expect(first.status()).toBe(200);
  const second = await request.get(`/player/${slug}`, {
    headers: { "fly-client-ip": "198.51.100.7", cookie: "something_else=2" },
  });
  expect(second.status()).toBe(200);

  const calls = await callsTo(request, `/api/v1/players/${slug}`);
  expect(calls).toHaveLength(1);
  expect(calls[0]!.clientIp).toBe("203.0.113.1");
  expect(calls[0]!.cookie).toBeNull();
});

test("a player who appears later is not stuck behind a cached 404", async ({ request }) => {
  const slug = `late-signing-${Date.now()}`;
  expect((await request.get(`/player/${slug}`)).status()).toBe(404);
  await control(request, {
    add: { slug, player: { id: 9999, name: "Late", full: "Late Signing", position: "FWD", price: 6.0 } },
  });
  expect((await request.get(`/player/${slug}`)).status()).toBe(200);
});

test("the sitemap fails loudly rather than dropping every player", async ({ request }) => {
  await control(request, { routes: { "/api/v1/players?limit=500": { status: 503 } } });
  // Runs before anything else reads the player index, so the cache is cold: a
  // failure is a 500, not a sitemap with every player missing.
  const failing = await request.get("/sitemap.xml");
  expect(failing.status()).toBe(500);
  await control(request, { reset: true });
  const ok = await request.get("/sitemap.xml");
  expect(ok.status()).toBe(200);
  const xml = await ok.text();
  expect(xml).toContain("/player/phil-foden");
  expect(xml).toContain("https://overtakefpl.example/players");
});

test("the players index exists, and links to player pages", async ({ request }) => {
  const response = await request.get("/players");
  expect(response.status()).toBe(200);
  expect(await response.text()).toContain('href="/player/phil-foden"');
});

test("the header's countdown and launch banner are decoration: a page survives them failing", async ({
  request,
}) => {
  await control(request, {
    routes: {
      "/api/v1/meta/season": { status: 503 },
      "/api/v1/billing/offer": { status: 503 },
    },
  });
  expect((await request.get("/how-to/find-your-fpl-league-id")).status()).toBe(200);
});

test("the default share image exists and every page points at it", async ({ request }) => {
  const image = await request.get("/og.png");
  expect(image.status()).toBe(200);
  expect(image.headers()["content-type"]).toBe("image/png");
  const bytes = await image.body();
  // PNG signature, then the IHDR width and height.
  expect(bytes.subarray(1, 4).toString()).toBe("PNG");
  expect(bytes.readUInt32BE(16)).toBe(1200);
  expect(bytes.readUInt32BE(20)).toBe(630);

  for (const path of ["/players", "/pricing", "/how-to/find-your-fpl-league-id"]) {
    const html = await (await request.get(path)).text();
    expect(html, path).toMatch(/<meta property="og:image" content="https:\/\/overtakefpl\.example\/og\.png"/);
    expect(html, path).toMatch(/<meta name="twitter:image" content="https:\/\/overtakefpl\.example\/og\.png"/);
  }
});

test("a league over the size limit is explained, not reported as a crash", async ({ page, request }) => {
  await control(request, {
    routes: {
      "/api/v1/leagues/314": {
        status: 422,
        body: {
          error: {
            code: "LEAGUE_TOO_LARGE",
            message: "That league has more than 200 managers.",
            error_id: "ref-limit-0001",
          },
        },
      },
      "/api/v1/leagues/777": {
        status: 500,
        body: { error: { code: "INTERNAL", message: "Something broke.", error_id: "ref-crash-0002" } },
      },
    },
  });

  await page.goto("/l/314");
  await expect(page.getByRole("heading", { name: /bigger than a mini-league/i })).toBeVisible();
  await expect(page.getByText(/up to 200 managers/i)).toBeVisible();
  await expect(page.getByText(/ref-limit-0001/)).toHaveCount(0);
  await expect(page.getByText(/^Reference/)).toHaveCount(0);

  // A genuine failure still carries its reference for support.
  await page.goto("/l/777");
  await expect(page.getByText(/ref-crash-0002/)).toBeVisible();
});

test("an unreachable API on a league page says so instead of crashing", async ({ page, request }) => {
  await control(request, { routes: { "/api/v1/leagues/888": { drop: true } } });
  await page.goto("/l/888");
  await expect(page.getByText(/could not reach our data service/i)).toBeVisible();
});

test("a signed-in header that cannot reach the API does not take the page down", async ({
  request,
}) => {
  await control(request, { routes: { "/api/v1/me": { drop: true } } });
  const response = await request.get("/how-to/find-your-fpl-league-id", {
    headers: { cookie: "overtake_session=not-a-real-session" },
  });
  expect(response.status()).toBe(200);
});
