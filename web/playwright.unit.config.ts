import { defineConfig } from "@playwright/test";

/**
 * Unit tests for the web app's pure logic — fetch failure handling, sharing,
 * formatting. No browser and no server: Playwright's runner is used only
 * because it is already here and compiles TypeScript with the `@/` paths.
 */
export default defineConfig({
  testDir: "./unit",
  testMatch: /.*\.spec\.ts$/,
  fullyParallel: true,
  reporter: process.env.CI ? [["github"], ["list"]] : "list",
  timeout: 10_000,
});
