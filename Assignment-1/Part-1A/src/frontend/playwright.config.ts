import { defineConfig, devices } from "@playwright/test";

// Chromium download is blocked by the corporate proxy and Edge forbids remote debugging by policy,
// so the manually installed Chrome Canary is used.
export default defineConfig({
  testDir: "e2e",
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  globalSetup: "./e2e/global-setup.ts",
  use: { baseURL: "http://127.0.0.1:5173" },
  projects: [{ name: "canary", use: { ...devices["Desktop Chrome"], channel: "chrome-canary" } }],
  webServer: [
    {
      command: "../../scripts/e2e-backend.sh",
      url: "http://127.0.0.1:8000/api/v1/health/ready",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 5173 --strictPort",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
