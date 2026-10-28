"use client";

import { useState } from "react";
import type { Side } from "@/lib/types";

export function TradeBar({
  ticker,
  onTickerChange,
  onTrade,
}: {
  ticker: string;
  onTickerChange: (ticker: string) => void;
  onTrade: (ticker: string, quantity: number, side: Side) => Promise<void>;
}) {
  const [quantity, setQuantity] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const trade = async (side: Side) => {
    const qty = Number(quantity);
    const t = ticker.trim().toUpperCase();
    setNotice(null);
    if (!t) return setError("Enter a ticker");
    if (!(qty > 0)) return setError("Enter a quantity greater than 0");
    setBusy(true);
    try {
      await onTrade(t, qty, side);
      setError(null);
      setNotice(`${side === "buy" ? "Bought" : "Sold"} ${qty} ${t}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const field =
    "num border border-line bg-ink px-2 py-1.5 text-sm focus:border-blue focus:outline-none placeholder:text-muted";

  return (
    <form
      onSubmit={(e) => e.preventDefault()}
      className="flex flex-wrap items-center gap-2 border border-line bg-panel px-3 py-2"
    >
      <span className="label mr-1">Market order</span>
      <input
        data-testid="trade-ticker"
        value={ticker}
        onChange={(e) => onTickerChange(e.target.value.toUpperCase())}
        placeholder="Ticker"
        aria-label="Ticker"
        maxLength={5}
        className={`${field} w-24 uppercase`}
      />
      <input
        data-testid="trade-quantity"
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
        placeholder="Qty"
        aria-label="Quantity"
        inputMode="decimal"
        type="number"
        min="0"
        step="any"
        className={`${field} w-24`}
      />
      <button
        data-testid="trade-buy"
        type="button"
        disabled={busy}
        onClick={() => trade("buy")}
        className="bg-up/90 px-4 py-1.5 font-display text-sm font-bold tracking-widest text-ink uppercase hover:bg-up disabled:opacity-50"
      >
        Buy
      </button>
      <button
        data-testid="trade-sell"
        type="button"
        disabled={busy}
        onClick={() => trade("sell")}
        className="bg-down/90 px-4 py-1.5 font-display text-sm font-bold tracking-widest text-ink uppercase hover:bg-down disabled:opacity-50"
      >
        Sell
      </button>
      {error && (
        <span data-testid="trade-error" role="alert" className="text-sm text-down">
          {error}
        </span>
      )}
      {!error && notice && <span className="text-sm text-up">{notice}</span>}
    </form>
  );
}
