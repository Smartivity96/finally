import { expect, type Page } from "@playwright/test";

export const DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"];

/** Parse a "$10,000.00" style string into a number. */
export function money(text: string | null): number {
  return Number((text ?? "").replace(/[^0-9.-]/g, ""));
}

/** Open the app and wait until the portfolio has loaded and prices are streaming. */
export async function openApp(page: Page) {
  await page.goto("/");
  await expect(page.getByTestId("connection-status")).toHaveAttribute("data-status", "connected");
  await expect(page.getByTestId("watchlist-row-AAPL")).toBeVisible();
  await expect(page.getByTestId("price-AAPL")).toHaveText(/\d/);
}

export async function cash(page: Page): Promise<number> {
  return money(await page.getByTestId("cash-balance").textContent());
}

/** Quantity held via the API (0 if no position). */
export async function heldQuantity(page: Page, ticker: string): Promise<number> {
  const res = await page.request.get("/api/portfolio");
  const body = await res.json();
  return body.positions.find((p: { ticker: string }) => p.ticker === ticker)?.quantity ?? 0;
}

export async function trade(page: Page, ticker: string, quantity: number, side: "buy" | "sell") {
  await page.getByTestId("trade-ticker").fill(ticker);
  await page.getByTestId("trade-quantity").fill(String(quantity));
  await page.getByTestId(`trade-${side}`).click();
}
