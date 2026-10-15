import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

/**
 * Regressions for the October 2026 new-visitor walkthrough. Each test names
 * the thing a visitor saw that was wrong.
 */

const LEAGUE_ID = process.env.E2E_LEAGUE_ID ?? "555001";

// Each test is its own visitor with its own rate-limit allowance, as separate
// people are in production (see playwright.config.ts). This file views the
// board many times a minute; as one visitor it would rightly be told to slow down.
test.beforeEach(async ({ context }, testInfo) => {
  const n = [...testInfo.testId].reduce((acc, ch) => (acc * 31 + ch.charCodeAt(0)) % 250, 7);
  await context.setExtraHTTPHeaders({ "fly-client-ip": `203.0.113.${n + 1}` });
});

interface BoardRow {
  manager: { entry_id: number; player_name: string; total: number };
  is_you: boolean;
}

async function board(request: APIRequestContext, entry?: number) {
  const query = entry ? `?entry=${entry}` : "";
  const response = await request.get(`/api/v1/leagues/${LEAGUE_ID}${query}`);
  expect(response.ok()).toBe(true);
  return (await response.json()) as { rows: BoardRow[]; deadline_gameweek: number | null };
}

/** You, and a rival you are ahead of on points. */
async function youAndARivalBehind(request: APIRequestContext) {
  const { rows } = await board(request);
  const sorted = [...rows].sort((a, b) => b.manager.total - a.manager.total);
  const you = sorted.find((row, i) => sorted.slice(i + 1).some((r) => r.manager.total < row.manager.total))!;
  const rival = sorted.find((row) => row.manager.total < you.manager.total)!;
  return { you: you.manager, rival: rival.manager };
}

async function pickFirstManager(page: Page) {
  await page.goto(`/l/${LEAGUE_ID}`);
  await page.getByLabel(/which one are you/i).selectOption({ index: 1 });
  await page.getByRole("button", { name: /show my odds/i }).click();
  await expect(page).toHaveURL(/entry=/);
}

test.describe("the league form", () => {
  test("submitting it empty says what to do", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /see my odds/i }).first().click();
    await expect(page.getByRole("main").getByRole("alert").first()).toContainText(
      /paste your league id or the league's url/i,
    );
    await expect(page).toHaveURL("/");
  });

  test("whitespace counts as empty", async ({ page }) => {
    await page.goto("/");
    await page.getByPlaceholder(/paste your league id/i).first().fill("   ");
    await page.getByRole("button", { name: /see my odds/i }).first().click();
    await expect(page.getByRole("main").getByRole("alert").first()).toContainText(
      /paste your league id or the league's url/i,
    );
  });

  test("it still works before the page's JavaScript has loaded", async ({ browser }) => {
    const context = await browser.newContext({ javaScriptEnabled: false });
    const page = await context.newPage();
    await page.goto("/");
    await page.getByPlaceholder(/paste your league id/i).first().fill(LEAGUE_ID);
    await page.getByRole("button", { name: /see my odds/i }).first().click();
    await expect(page).toHaveURL(new RegExp(`/l/${LEAGUE_ID}$`));

    await page.goto("/");
    await page.getByRole("button", { name: /see my odds/i }).first().click();
    await expect(page).toHaveURL(/\/l\?league=$/);
    await expect(page.getByText(/paste your league id or the league's url/i)).toBeVisible();
    await context.close();
  });
});

test.describe("the league board", () => {
  test("the headline says what 'realistically catchable' means", async ({ page }) => {
    await pickFirstManager(page);
    const headline = page.getByText(/still realistically catchable|you are top of|holding your place/i);
    await expect(headline).toBeVisible();
    if (await page.getByText(/still realistically catchable/i).isVisible()) {
      await expect(page.getByText(/at least a 1-in-20 \(5%\) chance/i)).toBeVisible();
    }
  });

  test("win chances come with the projection behind them", async ({ page }) => {
    await page.goto(`/l/${LEAGUE_ID}`);
    await expect(page.getByText(/P\(wins\) is each manager's chance of finishing top/i)).toBeVisible();
  });

  test("'needed per GW' is explained where it is shown", async ({ page }) => {
    await pickFirstManager(page);
    await expect(page.getByText(/needed per gw: extra points a gameweek, beyond what you are projected/i)).toBeVisible();
  });

  test("a legacy shared link does not make the reader the sharer", async ({ page, request }) => {
    const { rows } = await board(request);
    const sharer = rows[0]!.manager;
    await page.goto(`/l/${LEAGUE_ID}?entry=${sharer.entry_id}&utm_source=share&utm_medium=link`);
    await expect(page.getByLabel(/which one are you/i)).toBeVisible();
    await expect(page.getByText(/^you$/i)).toHaveCount(0);
  });

  test("a viewpoint you picked yourself is kept", async ({ page, request }) => {
    const { rows } = await board(request);
    const mine = rows[1]!.manager;
    await page.goto(`/l/${LEAGUE_ID}?entry=${mine.entry_id}`);
    await expect(page.getByLabel(/which one are you/i)).toHaveCount(0);
  });
});

test.describe("the rival page", () => {
  test("its tab title names the rival", async ({ page, request }) => {
    const { you, rival } = await youAndARivalBehind(request);
    await page.goto(`/l/${LEAGUE_ID}/vs/${rival.entry_id}?you=${you.entry_id}`);
    await expect(page).toHaveTitle(new RegExp(`^You vs ${rival.player_name} — .+ · Overtake$`));
  });

  test("the countdown is labelled with the gameweek whose deadline it is", async ({
    page,
    request,
  }) => {
    const { you, rival } = await youAndARivalBehind(request);
    const { deadline_gameweek } = await board(request);
    await page.goto(`/l/${LEAGUE_ID}/vs/${rival.entry_id}?you=${you.entry_id}`);
    await expect(page.getByText(`GW${deadline_gameweek} deadline`)).toBeVisible();
  });

  test("a rival you lead is not someone to 'catch'", async ({ page, request }) => {
    const { you, rival } = await youAndARivalBehind(request);
    await page.goto(`/l/${LEAGUE_ID}/vs/${rival.entry_id}?you=${you.entry_id}`);
    await expect(page.getByText(/points ahead/i)).toBeVisible();
    await expect(page.getByText(new RegExp(`what it takes to stay ahead of ${rival.player_name}`, "i"))).toBeVisible();
    await expect(page.getByText(new RegExp(`catch ${rival.player_name}`, "i"))).toHaveCount(0);
  });
});

test.describe("gameweek pages", () => {
  test("difficulty is labelled as difficulty, not printed like a score", async ({ page }) => {
    await page.goto("/gameweek/2");
    const table = page.getByRole("table", { name: /gameweek 2 fixtures/i });
    await expect(table.getByRole("columnheader", { name: /home fdr/i })).toBeVisible();
    await expect(table.getByRole("columnheader", { name: /away fdr/i })).toBeVisible();
    await expect(page.getByText(/average score \d+/i)).toBeVisible();
  });

  test("a gameweek nobody has finished has no average score", async ({ page }) => {
    await page.goto("/gameweek/4");
    await expect(page.getByText(/not played yet|in progress/i)).toBeVisible();
    await expect(page.getByText(/average score 0/i)).toHaveCount(0);
  });
});

test.describe("pricing", () => {
  test("every plan card has an action that works for a visitor", async ({ page }) => {
    await page.goto("/pricing");
    const buy = page.getByRole("link", { name: /create a free account to buy/i });
    await expect(buy).toHaveCount(2);
    await expect(buy.first()).toHaveAttribute("href", "/signin?next=/pricing");
    await expect(page.getByRole("link", { name: /start free/i })).toHaveAttribute("href", "/");
  });
});

test.describe("SEO routes", () => {
  test("the players index exists and the breadcrumb that points at it resolves", async ({
    page,
    request,
  }) => {
    const response = await page.goto("/players");
    expect(response?.status()).toBe(200);
    const first = page.locator('table a[href^="/player/"]').first();
    const href = await first.getAttribute("href");
    await page.goto(href!);
    await expect(page.getByRole("navigation", { name: "Breadcrumb" }).getByRole("link", { name: "Players" })).toHaveAttribute("href", "/players");
    expect((await request.get("/og.png")).headers()["content-type"]).toBe("image/png");
  });
});

test.describe("cost of a board view", () => {
  test("viewing the board does not spend the visitor's dossier allowance on prefetches", async ({
    page,
  }) => {
    const rivalPageRequests: string[] = [];
    page.on("request", (request) => {
      if (request.url().includes("/vs/")) rivalPageRequests.push(request.url());
    });
    await pickFirstManager(page);
    await page.waitForTimeout(1500);
    expect(rivalPageRequests).toEqual([]);
  });
});
