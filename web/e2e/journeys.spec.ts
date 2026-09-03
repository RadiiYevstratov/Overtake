import { expect, test } from "@playwright/test";

/**
 * The critical user journeys, end to end.
 *
 * The one that matters most is the first: a stranger arrives with a league ID,
 * sees a real probability without signing up, and reaches the dossier. If that
 * breaks, nothing else about the product matters.
 */

const LEAGUE_ID = process.env.E2E_LEAGUE_ID ?? "555001";

/** The landing page carries two league forms by design: the hero and the final CTA. */
function leagueInput(page: import("@playwright/test").Page) {
  return page.getByPlaceholder(/paste your league id/i).first();
}

/** Next injects its own aria-live route announcer, which also has role=alert. */
function formAlert(page: import("@playwright/test").Page) {
  return page.getByRole("main").getByRole("alert").first();
}

test.describe("the free hook", () => {
  test("a stranger can go from the landing page to real odds with no account", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: /stop trying to beat 13 million strangers/i }),
    ).toBeVisible();

    await leagueInput(page).fill(LEAGUE_ID);
    await page.getByRole("button", { name: /see my odds/i }).first().click();

    await expect(page).toHaveURL(new RegExp(`/l/${LEAGUE_ID}`));
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // A real probability, not a placeholder. Scoped to visible elements: the
    // desktop table and the mobile card list are both in the DOM, and only one
    // of them is displayed at any given viewport.
    await expect(page.locator("text=/\\d+%/ >> visible=true").first()).toBeVisible();
  });

  test("a league URL is accepted, not just a bare id", async ({ page }) => {
    await page.goto("/");
    await leagueInput(page).fill(
      `https://fantasy.premierleague.com/leagues/${LEAGUE_ID}/standings/c`,
    );
    await page.getByRole("button", { name: /see my odds/i }).first().click();
    await expect(page).toHaveURL(new RegExp(`/l/${LEAGUE_ID}`));
  });

  test("nonsense input is rejected without navigating", async ({ page }) => {
    await page.goto("/");
    await leagueInput(page).fill("not a league");
    await page.getByRole("button", { name: /see my odds/i }).first().click();
    await expect(formAlert(page)).toContainText(/does not look like/i);
    await expect(page).toHaveURL("/");
  });

  test("an unknown league gives a useful page rather than a crash", async ({ page }) => {
    const response = await page.goto("/l/999999999");
    expect(response?.status()).toBe(404);
    await expect(page.getByRole("heading", { name: /nothing here/i })).toBeVisible();
  });
});

test.describe("the aha moment", () => {
  test("picking yourself reveals the odds column and the rival cards", async ({ page }) => {
    await page.goto(`/l/${LEAGUE_ID}`);

    const picker = page.getByLabel(/which one are you/i);
    await expect(picker).toBeVisible();
    await picker.selectOption({ index: 1 });
    await page.getByRole("button", { name: /show my odds/i }).click();

    await expect(page.getByText(/you can realistically still catch|you are top of|holding your place/i)).toBeVisible();
    await expect(page.getByRole("heading", { name: /who you can catch/i })).toBeVisible();
  });

  test("the dossier shows the gap without an account, and locks the move", async ({
    page,
  }) => {
    await page.goto(`/l/${LEAGUE_ID}`);
    const picker = page.getByLabel(/which one are you/i);
    await picker.selectOption({ index: 1 });
    await page.getByRole("button", { name: /show my odds/i }).click();

    await page.getByRole("link", { name: /open .*dossier/i }).first().click();
    await expect(page).toHaveURL(/\/vs\//);

    // Everything above "THE MOVE" is free.
    await expect(page.getByRole("heading", { level: 1 })).toContainText(/you\s+vs/i);
    await expect(page.getByRole("heading", { name: /what it takes/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /where the gap is/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /pattern/i })).toBeVisible();

    // "THE MOVE" is not.
    await expect(page.getByRole("heading", { name: /^the move$/i })).toBeVisible();
    await expect(page.getByRole("link", { name: /create a free account/i })).toBeVisible();
  });

  test("every number carries its provenance", async ({ page }) => {
    await page.goto(`/l/${LEAGUE_ID}`);
    await expect(page.getByText(/simulated .* seasons/i)).toBeVisible();
    await expect(page.getByText(/seed/i).last()).toBeVisible();
  });
});

test.describe("the paywall", () => {
  test("a signed-out visitor is sent to sign in, not to a price", async ({ page }) => {
    await page.goto("/app");
    await expect(page).toHaveURL(/\/signin/);
  });

  test("pricing states both plans and the refund promise", async ({ page }) => {
    await page.goto("/pricing");
    await expect(page.getByText("€4.99").first()).toBeVisible();
    await expect(page.getByText("€29.99").first()).toBeVisible();
    await expect(page.getByRole("heading", { name: /refunds/i })).toBeVisible();
    await expect(page.getByText(/14-day right to withdraw/i)).toBeVisible();
  });

  test("the anti-dark-pattern commitments are on the page, testable", async ({ page }) => {
    await page.goto("/pricing");
    await expect(page.getByText(/no pre-ticked upsells/i)).toBeVisible();
    await expect(page.getByText(/no hidden auto-renew/i)).toBeVisible();
    await expect(page.getByText(/no cancellation gauntlet/i)).toBeVisible();
  });
});

test.describe("sign in", () => {
  test("the form refuses under-13s rather than taking their email", async ({ page }) => {
    await page.goto("/signin");
    await page.getByLabel(/email address/i).fill("kid@example.com");
    await page.getByLabel(/year of birth/i).fill(String(new Date().getFullYear() - 10));
    await expect(formAlert(page)).toContainText(/at least 13/i);
    await expect(page.getByRole("button", { name: /email me a sign-in link/i })).toBeDisabled();
  });

  test("it says plainly that we never ask for an FPL password", async ({ page }) => {
    await page.goto("/signin");
    await expect(
      page.getByRole("main").getByText(/never ask for your fpl password/i),
    ).toBeVisible();
  });
});

test.describe("public SEO pages", () => {
  test("a gameweek page carries our own projection, not just public stats", async ({
    page,
  }) => {
    await page.goto("/gameweek/3");
    await expect(page.getByRole("heading", { name: /gameweek 3/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /captain picks/i })).toBeVisible();
    await expect(page.getByRole("heading", { name: /differentials/i })).toBeVisible();
    await expect(page.getByText(/projections are ours, not fpl/i)).toBeVisible();
  });

  test("a comparison page answers the question from the mini-league angle", async ({
    page,
  }) => {
    // "Salah or Haaland" is the highest-intent query shape in FPL. The page has
    // to answer it, and answer it differently from everybody else.
    const index = await page.request.get("/api/v1/players?position=3&limit=4");
    const { players } = (await index.json()) as {
      players: { slug: string }[];
    };
    const pair = [players[0]!.slug, players[1]!.slug].sort().join("-vs-");

    await page.goto(`/compare/${pair}`);
    await expect(page.getByRole("heading", { level: 1 })).toContainText(/ or /i);
    await expect(
      page.getByRole("heading", { name: /the answer nobody else gives you/i }),
    ).toBeVisible();
    await expect(page.getByText(/projections are ours, not fpl/i)).toBeVisible();
  });

  test("a reversed comparison redirects to one canonical URL", async ({ page }) => {
    const index = await page.request.get("/api/v1/players?position=3&limit=4");
    const { players } = (await index.json()) as { players: { slug: string }[] };
    const sorted = [players[0]!.slug, players[1]!.slug].sort();
    const reversed = `${sorted[1]}-vs-${sorted[0]}`;

    await page.goto(`/compare/${reversed}`);
    // Two URLs for one comparison would split the ranking signal between them.
    await expect(page).toHaveURL(new RegExp(`/compare/${sorted[0]}-vs-${sorted[1]}$`));
  });

  test("an unknown player 404s rather than redirecting to a dead canonical", async ({
    page,
  }) => {
    const response = await page.goto("/compare/not-a-player-vs-also-not-a-player");
    expect(response?.status()).toBe(404);
  });

  test("the guides are indexable and link back into the product", async ({ page }) => {
    await page.goto("/mini-league/how-to-win-your-fpl-mini-league");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(leagueInput(page)).toBeVisible();
  });

  test("robots keeps league pages out of the index", async ({ request }) => {
    const response = await request.get("/robots.txt");
    expect(response.ok()).toBeTruthy();
    const body = await response.text();
    expect(body).toContain("Disallow: /l/");
    expect(body).toContain("Sitemap:");
  });

  test("the sitemap lists the indexed pages", async ({ request }) => {
    const response = await request.get("/sitemap.xml");
    expect(response.ok()).toBeTruthy();
    const body = await response.text();
    expect(body).toContain("/how-it-works");
    expect(body).toContain("/mini-league/how-to-win-your-fpl-mini-league");
    expect(body).not.toContain("/l/");
  });
});

test.describe("legal and consent", () => {
  test("the consent banner offers decline as prominently as accept", async ({ page }) => {
    await page.goto("/");
    const dialog = page.getByRole("dialog", { name: /analytics cookies/i });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole("button", { name: /no thanks/i })).toBeVisible();
    await expect(dialog.getByRole("button", { name: /allow/i })).toBeVisible();
  });

  test("declining dismisses it and the product still works", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /no thanks/i }).click();
    await expect(page.getByRole("dialog", { name: /analytics cookies/i })).toBeHidden();
    await page.goto(`/l/${LEAGUE_ID}`);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("the Premier League disclaimer is on every page", async ({ page }) => {
    for (const path of ["/", "/pricing", "/faq"]) {
      await page.goto(path);
      await expect(
        page.getByText(/not affiliated with, endorsed by, or associated with the premier league/i),
      ).toBeVisible();
    }
  });

  test("the legal pages exist and are readable", async ({ page }) => {
    for (const path of ["/privacy", "/terms", "/cookies"]) {
      await page.goto(path);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    }
  });
});

test.describe("accessibility basics", () => {
  test("there is a skip link and it works", async ({ page }) => {
    await page.goto("/");
    await page.keyboard.press("Tab");
    const skip = page.getByRole("link", { name: /skip to content/i });
    await expect(skip).toBeFocused();
  });

  test("the league board is a real table with a caption", async ({ page }) => {
    await page.goto(`/l/${LEAGUE_ID}`);
    // The desktop table is hidden on mobile viewports, which is expected.
    const table = page.locator("table").first();
    if (await table.isVisible()) {
      await expect(table.locator("caption")).toHaveCount(1);
      await expect(table.locator("th[scope='col']").first()).toBeVisible();
    }
  });

  test("every page has exactly one h1", async ({ page }) => {
    for (const path of ["/", "/pricing", "/faq", "/how-it-works", `/l/${LEAGUE_ID}`]) {
      await page.goto(path);
      await expect(page.locator("h1")).toHaveCount(1);
    }
  });

  test("the page has a language and a title", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("lang", "en-GB");
    await expect(page).toHaveTitle(/overtake/i);
  });
});

test.describe("security headers", () => {
  test("the response carries a content security policy and frame protection", async ({
    request,
  }) => {
    const response = await request.get("/");
    const headers = response.headers();
    expect(headers["content-security-policy"]).toContain("frame-ancestors 'none'");
    expect(headers["x-content-type-options"]).toBe("nosniff");
    expect(headers["x-frame-options"]).toBe("DENY");
    expect(headers["referrer-policy"]).toBe("strict-origin-when-cross-origin");
  });

  test("the server does not advertise itself", async ({ request }) => {
    const response = await request.get("/");
    expect(response.headers()["x-powered-by"]).toBeUndefined();
  });
});
