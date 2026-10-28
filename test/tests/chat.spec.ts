import { expect, test } from "@playwright/test";
import { cash, heldQuantity, openApp } from "./helpers";

// Requires LLM_MOCK=true (see planning/API.md §3 mock rules).

async function send(page: import("@playwright/test").Page, text: string) {
  await page.getByTestId("chat-input").fill(text);
  await page.getByTestId("chat-send").click();
}

test("mock chat 'buy' executes a trade shown inline and the position appears", async ({ page }) => {
  await openApp(page);
  const qtyBefore = await heldQuantity(page, "AAPL");
  const cashBefore = await cash(page);
  const assistant = page.locator('[data-testid="chat-message"][data-role="assistant"]');
  const countBefore = await assistant.count();

  await send(page, "Please buy some apple");

  const reply = assistant.nth(countBefore);
  await expect(reply).toContainText("Mock: buying 1 AAPL.");
  await expect(reply.getByTestId("chat-action")).toContainText(/Bought 1 AAPL/);
  await expect(page.getByTestId("chat-loading")).toHaveCount(0);
  await expect(page.getByTestId("position-row-AAPL")).toBeVisible();
  await expect.poll(() => cash(page)).toBeLessThan(cashBefore);
  expect(await heldQuantity(page, "AAPL")).toBeCloseTo(qtyBefore + 1);
});

test("mock chat 'watch' adds PYPL to the watchlist", async ({ page }) => {
  await page.request.delete("/api/watchlist/PYPL");
  await openApp(page);
  await expect(page.getByTestId("watchlist-row-PYPL")).toHaveCount(0);
  const assistant = page.locator('[data-testid="chat-message"][data-role="assistant"]');
  const countBefore = await assistant.count();

  await send(page, "watch paypal for me");

  const reply = assistant.nth(countBefore);
  await expect(reply).toContainText("Mock: adding PYPL to your watchlist.");
  await expect(reply.getByTestId("chat-action")).toContainText(/Added PYPL/);
  await expect(page.getByTestId("watchlist-row-PYPL")).toBeVisible();

  // Clean up so other tests start without PYPL.
  await page.request.delete("/api/watchlist/PYPL");
});
