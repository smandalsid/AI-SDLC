import { expect, test, type Page } from "@playwright/test";
import { resetDatabase, signIn } from "./support";

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
