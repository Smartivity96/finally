import { expect, test } from "@playwright/test";
import { DEFAULT_TICKERS, cash, openApp } from "./helpers";

// Assumes a fresh database (see README): default watchlist and $10,000 cash.
test("fresh start shows default watchlist, $10k cash and live prices", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
  await openApp(page);

  for (const t of DEFAULT_TICKERS) {
    await expect(page.getByTestId(`watchlist-row-${t}`)).toBeVisible();
  }
  expect(await cash(page)).toBe(10000);
  await expect(page.getByTestId("connection-status")).toHaveAttribute("data-status", "connected");

  // Prices are streaming: the AAPL price text changes within a few seconds.
  const price = page.getByTestId("price-AAPL");
  const first = await price.textContent();
  await expect(price).not.toHaveText(first ?? "", { timeout: 10_000 });

  expect(errors).toEqual([]);
});
