import { expect, test } from "@playwright/test";
import { mockPassword, resetDatabase, signIn } from "./support";

const MAX_INTERACTIONS = 3;
const BOOKING_BUDGET_MS = 30_000;
const VIEW_BUDGET_MS = 2_000;

test.beforeEach(() => {
  resetDatabase();
});

// The dev server compiles modules on first request; warm it so the budgets measure steady state.
test.beforeAll(async ({ browser }) => {
  const page = await browser.newPage({ baseURL: "http://127.0.0.1:5173" });
  await signIn(page, "asha");
  await page.getByRole("link", { name: /Bus A/ }).click();
  await expect(page.getByRole("button", { name: "Seat 1, available" })).toBeVisible();
  await page.close();
});

function counted(): {
  interactions: () => number;
  act: (step: () => Promise<unknown>) => Promise<void>;
} {
  let count = 0;
  return {
    interactions: () => count,
    act: async (step) => {
      count += 1;
      await step();
    },
  };
}

test("the bus list is visible within 2 seconds of opening the application", async ({ page }) => {
  await signIn(page, "asha");
  const started = Date.now();

  await page.goto("/");
  await expect(page.getByRole("link", { name: /Bus A/ })).toBeVisible({ timeout: VIEW_BUDGET_MS });

  expect(Date.now() - started).toBeLessThan(VIEW_BUDGET_MS);
});

test("the seat list is visible within 2 seconds of choosing a bus", async ({ page }) => {
  await signIn(page, "asha");
  await expect(page.getByRole("link", { name: /Bus B/ })).toBeVisible();

  const started = Date.now();
  await page.getByRole("link", { name: /Bus B/ }).click();
  await expect(page.getByRole("button", { name: "Seat 30, available" })).toBeVisible({
    timeout: VIEW_BUDGET_MS,
  });

  expect(Date.now() - started).toBeLessThan(VIEW_BUDGET_MS);
});

test("one seat is booked in at most 3 interactions and under 30 seconds", async ({ page }) => {
  const { act, interactions } = counted();
  await signIn(page, "asha");
  await expect(page.getByRole("link", { name: /Bus A/ })).toBeVisible();
  const started = Date.now();

  await act(() => page.getByRole("link", { name: /Bus A/ }).click());
  await act(() => page.getByRole("button", { name: "Seat 2, available" }).click());
  await act(() => page.getByRole("button", { name: "Confirm booking" }).click());
  await expect(page.getByText("Booked seat 2.")).toBeVisible();

  expect(interactions()).toBeLessThanOrEqual(MAX_INTERACTIONS);
  expect(Date.now() - started).toBeLessThan(BOOKING_BUDGET_MS);
});

test("the bus list is reached from the sign-in screen in at most 3 interactions", async ({
  page,
}) => {
  const { act, interactions } = counted();
  await page.goto("/login");
  const started = Date.now();

  await act(() => page.getByLabel("Username").fill("asha"));
  await act(() => page.getByLabel("Password").fill(mockPassword("asha")));
  const submitted = Date.now();
  await act(() => page.getByRole("button", { name: "Sign in" }).click());
  await expect(page.getByRole("heading", { name: "Buses" })).toBeVisible();
  await expect(page.getByRole("link", { name: /Bus A/ })).toBeVisible({ timeout: VIEW_BUDGET_MS });

  expect(interactions()).toBeLessThanOrEqual(MAX_INTERACTIONS);
  expect(Date.now() - started).toBeLessThan(BOOKING_BUDGET_MS);
  expect(Date.now() - submitted).toBeLessThan(VIEW_BUDGET_MS);
});

test("sign-in works with the keyboard alone", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();

  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Username")).toBeFocused();
  await page.keyboard.type("asha");
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Password")).toBeFocused();
  await page.keyboard.type(mockPassword("asha"));
  await page.keyboard.press("Enter");

  await expect(page.getByRole("heading", { name: "Buses" })).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Sign out" })).toBeFocused();
});
