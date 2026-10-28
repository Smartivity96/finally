import { expect, test } from "@playwright/test";
import { openApp, trade } from "./helpers";

/** Mirror of the colour rule in PLAN §13.3.3: P&L % clamped to ±10%, slate → green/red. */
function expectedHeatColor(pnlPercent: number): number[] {
  const t = Math.max(-1, Math.min(1, pnlPercent / 10));
  const base = [36, 44, 58];
  const target = t >= 0 ? [22, 163, 98] : [220, 58, 64];
  return base.map((c, i) => c + (target[i] - c) * Math.abs(t));
}

test("heatmap and P&L chart render after a trade", async ({ page }) => {
  await openApp(page);
  await trade(page, "AMZN", 1, "buy");
  await expect(page.getByTestId("position-row-AMZN")).toBeVisible();

  // Heatmap: a cell for the position, with a non-zero size and a colour matching its P&L.
  const cell = page.getByTestId("heatmap-cell-AMZN");
  await expect(cell).toBeVisible();
  const box = await cell.boundingBox();
  expect(box!.width).toBeGreaterThan(10);
  expect(box!.height).toBeGreaterThan(10);
  // Read title and colour in one go so they come from the same render.
  const { title, bg } = await cell.evaluate((el) => ({
    title: el.getAttribute("title") ?? "",
    bg: getComputedStyle(el).backgroundColor,
  }));
  const pct = Number(title.split(" ")[1].replace("−", "-").replace(/[+%]/g, ""));
  const rgb = bg.match(/\d+/g)!.map(Number);
  expectedHeatColor(pct).forEach((c, i) => expect(Math.abs(rgb[i] - c)).toBeLessThanOrEqual(3));

  // P&L chart: backend has snapshots (startup + this trade) and the chart draws a canvas.
  const history = await (await page.request.get("/api/portfolio/history")).json();
  expect(history.length).toBeGreaterThanOrEqual(2);
  const chart = page.getByTestId("pnl-chart");
  await expect(chart.locator("canvas").first()).toBeVisible();
  const chartBox = await chart.boundingBox();
  expect(chartBox!.height).toBeGreaterThan(50);
});
