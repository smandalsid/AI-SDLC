/// <reference types="node" />
import { expect, type APIRequestContext, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const RESET_SCRIPT = fileURLToPath(new URL("../../../scripts/e2e-reset.sh", import.meta.url));
const ENV_FILE = fileURLToPath(new URL("../../../.env", import.meta.url));

/** Returns the test database to the seeded state (3 buses, 3 users, no bookings). */
export function resetDatabase(): void {
  execFileSync(RESET_SCRIPT, { stdio: "pipe" });
}

/** The only reader of the git-ignored .env here; the password is never printed or stored. */
function mockPassword(username: string): string {
  const line = readFileSync(ENV_FILE, "utf8")
    .split("\n")
    .find((candidate) => candidate.startsWith("MOCK_USER_PASSWORDS="));
  if (line === undefined) throw new Error("MOCK_USER_PASSWORDS is not set in .env");
  const raw = line.slice("MOCK_USER_PASSWORDS=".length).trim().replace(/^(['"])(.*)\1$/, "$2");
  const passwords = JSON.parse(raw) as Record<string, string>;
  const password = passwords[username];
  if (password === undefined) throw new Error(`no mock password for ${username}`);
  return password;
}

/** Signs in through the sign-in screen and waits for the bus list. */
export async function signIn(page: Page, username: string): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Username").fill(username);
  await page.getByLabel("Password").fill(mockPassword(username));
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Buses" })).toBeVisible();
}

/** Authorization header for direct API calls made with the Playwright request context. */
export async function authorization(
  request: APIRequestContext,
  username: string,
): Promise<Record<string, string>> {
  const response = await request.post("/api/v1/auth/login", {
    data: { username, password: mockPassword(username) },
  });
  const body = (await response.json()) as { access_token: string };
  return { Authorization: `Bearer ${body.access_token}` };
}
