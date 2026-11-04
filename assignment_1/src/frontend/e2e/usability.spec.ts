import { expect, test } from "@playwright/test";
import { resetDatabase, signIn } from "./support";

const MAX_INTERACTIONS = 5;
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

test("one seat is booked in at most 5 interactions and under 30 seconds", async ({ page }) => {
  const { act, interactions } = counted();
  await signIn(page, "asha");
  await expect(page.getByRole("link", { name: /Bus A/ })).toBeVisible();
  const started = Date.now();

  await act(() => page.getByRole("link", { name: /Bus A/ }).click());
  await act(() => page.getByLabel("Booking as").selectOption({ label: "Ravi" }));
  await act(() => page.getByRole("button", { name: "Seat 2, available" }).click());
  await act(() => page.getByRole("button", { name: "Confirm booking" }).click());
  await expect(page.getByText("Booked seat 2.")).toBeVisible();

  expect(interactions()).toBeLessThanOrEqual(MAX_INTERACTIONS);
  expect(Date.now() - started).toBeLessThan(BOOKING_BUDGET_MS);
});
