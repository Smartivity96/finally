import { expect, test } from "@playwright/test";
import { openApp } from "./helpers";

// Note: context.setOffline() does not cut an already-open EventSource in Chromium,
// so the drop is simulated by blocking the stream request and then restoring it.
const STREAM = "**/api/stream/prices";

test("connection status recovers when the price stream comes back", async ({ page }) => {
  // Block the stream from the start: the indicator must not claim to be connected.
  await page.route(STREAM, (route) => route.abort());
  await page.goto("/");
  await expect(page.getByTestId("watchlist-row-AAPL")).toBeVisible();
  await expect(page.getByTestId("connection-status")).not.toHaveAttribute("data-status", "connected");

  // Restore the stream: EventSource retries on its own and the indicator turns green.
  await page.unroute(STREAM);
  await expect(page.getByTestId("connection-status")).toHaveAttribute("data-status", "connected", {
    timeout: 15_000,
  });
  const price = page.getByTestId("price-AAPL");
  await expect(price).toHaveText(/\d/);
  const first = await price.textContent();
  await expect(price).not.toHaveText(first ?? "");
});

