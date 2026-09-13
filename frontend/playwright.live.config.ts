import { defineConfig } from "@playwright/test";

const baseURL = process.env.RECALLNEXT_LIVE_BASE_URL;
if (!baseURL) {
  throw new Error("RECALLNEXT_LIVE_BASE_URL is required for the live Exasol browser check");
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: "live-exasol.spec.ts",
  workers: 1,
  reporter: "list",
  use: {
    baseURL,
    channel: process.env.CI ? undefined : "msedge",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
});
