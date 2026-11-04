import { expect, test } from "@playwright/test";
import { authorization, resetDatabase, signIn } from "./support";

test.beforeEach(() => {
  resetDatabase();
});

test("seats booked through the UI are still booked after a reload", async ({ page }) => {
  await signIn(page, "asha");
  await page.getByRole("link", { name: /Bus A/ }).click();
  await page.getByLabel("Booking as").selectOption({ label: "Asha" });
  await page.getByRole("button", { name: "Seat 5, available" }).click();
  await page.getByRole("button", { name: "Seat 6, available" }).click();
  await page.getByRole("button", { name: "Confirm booking" }).click();

  await expect(page.getByText("Booked seats 5, 6.")).toBeVisible();
  await page.reload();

  for (const seat of [5, 6]) {
    await expect(page.getByRole("button", { name: `Seat ${seat}, booked` })).toBeDisabled();
  }
});

test("an unconfirmed selection is discarded on reload and nothing is stored", async ({
  page,
  request,
}) => {
  await signIn(page, "asha");
  await page.goto("/buses/1");
  await page.getByRole("button", { name: "Seat 8, available" }).click();
  await expect(page.getByRole("button", { name: "Seat 8, selected" })).toBeVisible();

  await page.reload();

  await expect(page.getByRole("button", { name: "Seat 8, available" })).toBeVisible();
  const headers = await authorization(request, "asha");
  const bus = (await (await request.get("/api/v1/buses/1", { headers })).json()) as {
    seats: { seat_number: number; status: string }[];
  };
  expect(bus.seats.find((seat) => seat.seat_number === 8)?.status).toBe("available");
});
