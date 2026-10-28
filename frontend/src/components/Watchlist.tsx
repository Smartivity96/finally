"use client";

import { useState } from "react";
import type { PriceStream } from "@/hooks/usePriceStream";
import { dailyChangePercent } from "@/lib/calc";
import { fmtPct, signClass } from "@/lib/format";
import type { WatchlistItem } from "@/lib/types";
import { Panel } from "./Panel";
import { PriceCell } from "./PriceCell";
import { Sparkline } from "./Sparkline";

export function Watchlist({
  items,
  stream,
  selected,
  onSelect,
  onAdd,
  onRemove,
}: {
  items: WatchlistItem[];
  stream: PriceStream;
  selected: string | null;
  onSelect: (ticker: string) => void;
  onAdd: (ticker: string) => Promise<void>;
  onRemove: (ticker: string) => Promise<void>;
}) {
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const ticker = input.trim().toUpperCase();
    if (!ticker) return;
    try {
      await onAdd(ticker);
      setInput("");
      setError(null);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <Panel title="Watchlist" right={<span className="label">{items.length}</span>} className="h-full">
      <div className="flex h-full flex-col">
        <form onSubmit={submit} className="flex gap-1 border-b border-line p-2">
          <input
            data-testid="watchlist-add-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Add ticker"
            maxLength={5}
            aria-label="Ticker to add"
            className="num min-w-0 flex-1 border border-line bg-ink px-2 py-1 text-sm uppercase placeholder:normal-case placeholder:text-muted focus:border-blue focus:outline-none"
          />
          <button
            data-testid="watchlist-add-button"
            type="submit"
            className="border border-line px-3 text-sm text-blue hover:border-blue"
          >
            Add
          </button>
        </form>
        {error && <p className="px-2 pt-1 text-xs text-down">{error}</p>}

        <ul className="min-h-0 flex-1 overflow-y-auto">
          {items.map((item) => {
            const live = stream.prices[item.ticker];
            const price = live?.price ?? item.price;
            const direction = live?.direction ?? item.direction;
            const change = price != null ? dailyChangePercent(price, stream.firstPrices[item.ticker]) : 0;
            const isSelected = selected === item.ticker;
            return (
              <li
                key={item.ticker}
                data-testid={`watchlist-row-${item.ticker}`}
                onClick={() => onSelect(item.ticker)}
                className={`group grid cursor-pointer grid-cols-[3.5rem_1fr_auto_1rem] items-center gap-x-2 border-b border-l-2 border-b-line/60 px-2 py-1.5 hover:bg-raised ${
                  isSelected ? "border-l-accent bg-raised" : "border-l-transparent"
                }`}
              >
                <span className="font-display text-sm font-semibold tracking-wide">{item.ticker}</span>
                <div className="justify-self-end">
                  <Sparkline points={stream.history[item.ticker]} />
                </div>
                <div className="flex flex-col items-end leading-tight">
                  <PriceCell price={price} direction={direction} testId={`price-${item.ticker}`} className="text-sm" />
                  <span className={`num text-[11px] ${signClass(change)}`}>{fmtPct(change)}</span>
                </div>
                <button
                  type="button"
                  data-testid={`watchlist-remove-${item.ticker}`}
                  aria-label={`Remove ${item.ticker}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemove(item.ticker).catch((err) => setError((err as Error).message));
                  }}
                  className="text-xs text-muted opacity-0 group-hover:opacity-100 hover:text-down focus:opacity-100"
                >
                  ✕
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </Panel>
  );
}
