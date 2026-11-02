import { defineConfig, devices } from "@playwright/test";

// The corporate proxy blocks the Chromium download, so the installed Microsoft Edge is used.
export default defineConfig({
  testDir: "e2e",
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  globalSetup: "./e2e/global-setup.ts",
  use: { baseURL: "http://127.0.0.1:5173" },
  projects: [{ name: "edge", use: { ...devices["Desktop Edge"], channel: "msedge" } }],
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
