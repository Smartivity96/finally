import { expect, test } from "@playwright/test";
import { cash, heldQuantity, openApp, trade } from "./helpers";

test("buy shares: cash decreases and the position appears", async ({ page }) => {
  await openApp(page);
  const cashBefore = await cash(page);
  const qtyBefore = await heldQuantity(page, "MSFT");

  await trade(page, "MSFT", 2, "buy");

  await expect(page.getByTestId("position-row-MSFT")).toBeVisible();
  await expect.poll(() => cash(page)).toBeLessThan(cashBefore);
  expect(await heldQuantity(page, "MSFT")).toBeCloseTo(qtyBefore + 2);
  await expect(page.getByTestId("trade-error")).toHaveCount(0);
});

test("sell shares: cash increases and the position updates, then disappears", async ({ page }) => {
  await openApp(page);
  await trade(page, "JPM", 3, "buy");
  await expect(page.getByTestId("position-row-JPM")).toBeVisible();
  const held = await heldQuantity(page, "JPM");

  // Partial sell: position stays with a smaller quantity.
  let cashBefore = await cash(page);
  await trade(page, "JPM", 1, "sell");
  await expect.poll(() => cash(page)).toBeGreaterThan(cashBefore);
  expect(await heldQuantity(page, "JPM")).toBeCloseTo(held - 1);
  await expect(page.getByTestId("position-row-JPM")).toBeVisible();

  // Sell the rest: position disappears.
  cashBefore = await cash(page);
  await trade(page, "JPM", held - 1, "sell");
  await expect.poll(() => cash(page)).toBeGreaterThan(cashBefore);
  await expect(page.getByTestId("position-row-JPM")).toHaveCount(0);
  expect(await heldQuantity(page, "JPM")).toBe(0);
});

test("insufficient cash shows a trade error", async ({ page }) => {
  await openApp(page);
  const cashBefore = await cash(page);

  await trade(page, "NVDA", 1_000_000, "buy");

  await expect(page.getByTestId("trade-error")).toContainText(/insufficient cash/i);
  expect(await cash(page)).toBe(cashBefore);
});
