import { defineConfig } from "@playwright/test";

const WEB_PORT = 3100;
const API_PORT = 8765;

/**
 * The production build against a scriptable fake API: what pages actually
 * answer — status codes included — when the API rate-limits, fails, drops the
 * connection or comes back. Needs `npm run build` first.
 */
export default defineConfig({
  testDir: "./resilience",
  testMatch: /.*\.spec\.ts$/,
  fullyParallel: false,
  workers: 1,
  reporter: process.env.CI ? [["github"], ["list"]] : "list",
  timeout: 60_000,
  use: { baseURL: `http://127.0.0.1:${WEB_PORT}` },
  webServer: [
    {
      command: "node resilience/mock-api.mjs",
      url: `http://127.0.0.1:${API_PORT}/__calls`,
      env: { MOCK_API_PORT: String(API_PORT) },
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      // A fresh data cache every run, so nothing is served from a previous one.
      command: `node resilience/clean-cache.mjs && npx next start -p ${WEB_PORT}`,
      url: `http://127.0.0.1:${WEB_PORT}/og.png`,
      env: {
        API_INTERNAL_URL: `http://127.0.0.1:${API_PORT}`,
        INTERNAL_PROXY_SECRET: "resilience-test-secret-that-is-long-enough",
        NEXT_PUBLIC_SITE_URL: "https://overtakefpl.example",
      },
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
