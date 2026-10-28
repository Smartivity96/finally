"use client";

import type { PriceStream } from "@/hooks/usePriceStream";
import { dailyChangePercent } from "@/lib/calc";
import { fmtPct, fmtSigned, signClass } from "@/lib/format";
import { LineChart } from "./LineChart";
import { PriceCell } from "./PriceCell";

const EMPTY: never[] = [];

export function MainChart({ ticker, stream }: { ticker: string | null; stream: PriceStream }) {
  const live = ticker ? stream.prices[ticker] : undefined;
  const first = ticker ? stream.firstPrices[ticker] : undefined;
  const change = live && first ? live.price - first : 0;
  const changePct = live ? dailyChangePercent(live.price, first) : 0;

  return (
    <section className="flex h-full min-h-0 flex-col border border-line bg-panel">
      <header className="flex shrink-0 items-end gap-4 border-b border-line px-4 py-2">
        <span className="font-display text-3xl leading-none font-bold tracking-wide text-accent">
          {ticker ?? "—"}
        </span>
        <PriceCell price={live?.price} direction={live?.direction} className="text-2xl leading-none font-semibold" />
        {live && (
          <span className={`num text-sm leading-none ${signClass(change)}`}>
            {fmtSigned(change)} ({fmtPct(changePct)})
          </span>
        )}
        <span className="label ml-auto">Since session open</span>
      </header>
      <div className="min-h-0 flex-1 p-1">
        <LineChart
          points={(ticker && stream.history[ticker]) || EMPTY}
          color="#209dd7"
          testId="main-chart"
        />
      </div>
    </section>
  );
}
