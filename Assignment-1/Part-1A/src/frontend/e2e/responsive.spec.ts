import { expect, test, type Page } from "@playwright/test";
import { resetDatabase, signIn } from "./support";

const WIDTHS = [320, 768, 1280];
const HEIGHT = 800;

test.beforeEach(() => {
  resetDatabase();
});

async function expectNoHorizontalScroll(page: Page): Promise<void> {
  const { scrollWidth, innerWidth } = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  expect(scrollWidth).toBeLessThanOrEqual(innerWidth);
}

for (const width of WIDTHS) {
  test(`the bus list does not scroll horizontally at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: HEIGHT });
    await signIn(page, "asha");

    await page.goto("/");

    await expect(page.getByRole("link", { name: /Bus C/ })).toBeVisible();
    await expectNoHorizontalScroll(page);
  });

  test(`the seat page does not scroll horizontally at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: HEIGHT });
    await signIn(page, "asha");

    // Bus C has the most seats (40), so it is the widest grid.
    await page.goto("/buses/3");

    await expect(page.getByRole("button", { name: "Seat 40, available" })).toBeVisible();
    await expectNoHorizontalScroll(page);
  });

  test(`a booking can be made and confirmed at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: HEIGHT });
    await signIn(page, "meera");
    await page.goto("/buses/3");

    await page.getByLabel("Booking as").selectOption({ label: "Meera" });
    await page.getByRole("button", { name: "Seat 40, available" }).click();
    await page.getByRole("button", { name: "Confirm booking" }).click();

    await expect(page.getByText("Booked seat 40.")).toBeVisible();
    await expectNoHorizontalScroll(page);
  });
}
