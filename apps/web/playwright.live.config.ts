import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./live-tests", workers: 1,
  use: { baseURL: process.env.FLOWSTATE_LIVE_URL || "http://localhost:13000", trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["iPhone 13"], defaultBrowserType: "chromium" } },
  ],
});
