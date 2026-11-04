import { expect, test, type Page } from "@playwright/test";
import { authorization, mockPassword, resetDatabase, signIn } from "./support";

// Same key as src/api/session.ts; the page is given a token the server never issued.
const TOKEN_KEY = "bus-booking.session-token";

test.beforeEach(() => {
  resetDatabase();
});

function watchBusRequests(page: Page): () => number {
  let requests = 0;
  page.on("request", (request) => {
    if (request.url().includes("/api/v1/buses")) requests += 1;
  });
  return () => requests;
}

async function expectOnlySignIn(page: Page): Promise<void> {
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await expect(page.getByText("Bus A")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Seat \d+/ })).toHaveCount(0);
}

for (const address of ["/", "/buses/1"]) {
  test(`a signed-out visit to ${address} shows only the sign-in screen`, async ({ page }) => {
    const busRequests = watchBusRequests(page);

    await page.goto(address);

    await expectOnlySignIn(page);
    expect(busRequests()).toBe(0);
  });
}

test("a token the server never issued leads back to the sign-in screen", async ({ page }) => {
  await page.addInitScript((key) => sessionStorage.setItem(key, "made-up-token"), TOKEN_KEY);

  await page.goto("/");

  await expectOnlySignIn(page);
  expect(await page.evaluate((key) => sessionStorage.getItem(key), TOKEN_KEY)).toBeNull();
});

test("a second tab does not share the session of the first", async ({ page }) => {
  await signIn(page, "asha");

  const second = await page.context().newPage();
  await second.goto("/");

  await expectOnlySignIn(second);
  await expect(page.getByRole("heading", { name: "Buses" })).toBeVisible();
});

async function expectHeader(page: Page, name: string): Promise<void> {
  await expect(page.getByRole("banner")).toContainText(name);
  await expect(page.getByRole("button", { name: "Sign out" })).toBeVisible();
}

test("the header with the name and Sign out is visible on the bus list and the seat page", async ({
  page,
}) => {
  await signIn(page, "ravi");
  await expectHeader(page, "Ravi");

  await page.getByRole("link", { name: /Bus A/ }).click();

  await expect(page.getByRole("button", { name: "Seat 1, available" })).toBeVisible();
  await expectHeader(page, "Ravi");
});

test("after sign-out Back shows only the sign-in screen and the old token is refused", async ({
  page,
  request,
}) => {
  await signIn(page, "asha");
  await page.getByRole("link", { name: /Bus A/ }).click();
  await expect(page.getByRole("button", { name: "Seat 1, available" })).toBeVisible();
  const token = await page.evaluate((key) => sessionStorage.getItem(key), TOKEN_KEY);
  expect(token).not.toBeNull();

  await page.getByRole("button", { name: "Sign out" }).click();
  await expectOnlySignIn(page);
  await page.goBack();

  await expectOnlySignIn(page);
  expect(await page.evaluate((key) => sessionStorage.getItem(key), TOKEN_KEY)).toBeNull();
  const replay = await request.get("/api/v1/buses", {
    headers: { Authorization: `Bearer ${token ?? ""}` },
  });
  expect(replay.status()).toBe(401);
});

test("signing in again after a sign-out works and issues a new token", async ({ page, request }) => {
  await signIn(page, "asha");
  const first = await page.evaluate((key) => sessionStorage.getItem(key), TOKEN_KEY);
  await page.getByRole("button", { name: "Sign out" }).click();
  await expectOnlySignIn(page);

  await signIn(page, "asha");

  const second = await page.evaluate((key) => sessionStorage.getItem(key), TOKEN_KEY);
  expect(second).not.toBeNull();
  expect(second).not.toBe(first);
  await expectHeader(page, "Asha");
  const headers = await authorization(request, "asha");
  expect((await request.get("/api/v1/buses", { headers })).status()).toBe(200);
});

test("a sign-out in one tab leaves the session of a second tab alone", async ({ page }) => {
  await signIn(page, "asha");
  const second = await page.context().newPage();
  await second.goto("/login");
  await second.getByLabel("Username").fill("ravi");
  await second.getByLabel("Password").fill(mockPassword("ravi"));
  await second.getByRole("button", { name: "Sign in" }).click();
  await expect(second.getByRole("heading", { name: "Buses" })).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();

  await expectOnlySignIn(page);
  await second.reload();
  await expect(second.getByRole("heading", { name: "Buses" })).toBeVisible();
});

test("an expired session returns to the sign-in screen with the expiry message and no bus data", async ({
  page,
}) => {
  await signIn(page, "asha");
  // A 30-minute wait is not practical, so the server's answer for an expired session is simulated.
  await page.route("**/api/v1/buses**", (route) =>
    route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({
        error: { code: "unauthenticated", message: "Authentication required." },
      }),
    }),
  );

  await page.reload();

  await expectOnlySignIn(page);
  await expect(page.getByRole("alert")).toHaveText(
    "Your session has expired. Please sign in again.",
  );
  expect(await page.evaluate((key) => sessionStorage.getItem(key), TOKEN_KEY)).toBeNull();
});

test("a plain first visit to the sign-in screen shows no expiry message", async ({ page }) => {
  await page.goto("/login");

  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await expect(page.getByRole("alert")).toHaveCount(0);
});
