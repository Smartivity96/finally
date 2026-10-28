import { expect, test } from "@playwright/test";
import { openApp } from "./helpers";

test("add and remove a ticker from the watchlist", async ({ page }) => {
  // Start from a known state: make sure PYPL is not watched (another test may add it).
  await page.request.delete("/api/watchlist/PYPL");
  await openApp(page);
  await expect(page.getByTestId("watchlist-row-PYPL")).toHaveCount(0);

  await page.getByTestId("watchlist-add-input").fill("pypl");
  await page.getByTestId("watchlist-add-button").click();
  await expect(page.getByTestId("watchlist-row-PYPL")).toBeVisible();
  // The new ticker gets priced by the stream.
  await expect(page.getByTestId("price-PYPL")).toHaveText(/\d/);

  await page.getByTestId("watchlist-row-PYPL").hover();
  await page.getByTestId("watchlist-remove-PYPL").click();
  await expect(page.getByTestId("watchlist-row-PYPL")).toHaveCount(0);

  // Persisted server-side.
  const list = await (await page.request.get("/api/watchlist")).json();
  expect(list.map((w: { ticker: string }) => w.ticker)).not.toContain("PYPL");
});
