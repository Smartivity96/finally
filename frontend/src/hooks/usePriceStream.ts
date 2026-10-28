"use client";

import { useEffect, useState } from "react";
import type { PriceMap } from "@/lib/calc";
import type { ConnectionStatus, PriceUpdate } from "@/lib/types";

export interface PricePoint {
  time: number; // Unix seconds
  value: number;
}

const MAX_POINTS = 600; // ~5 min at 500ms
const STALE_MS = 15_000; // no event for this long → treat as disconnected

export interface PriceStream {
  prices: PriceMap;
  firstPrices: Record<string, number>;
  history: Record<string, PricePoint[]>;
  status: ConnectionStatus;
}

/** Subscribes to /api/stream/prices and accumulates prices + per-ticker history since page load. */
export function usePriceStream(url = "/api/stream/prices"): PriceStream {
  const [state, setState] = useState<PriceStream>({
    prices: {},
    firstPrices: {},
    history: {},
    status: "reconnecting",
  });

  useEffect(() => {
    const es = new EventSource(url);
    let staleTimer: ReturnType<typeof setTimeout> | undefined;

    const setStatus = (status: ConnectionStatus) =>
      setState((s) => (s.status === status ? s : { ...s, status }));

    const armStale = () => {
      clearTimeout(staleTimer);
      staleTimer = setTimeout(() => setStatus("disconnected"), STALE_MS);
    };

    es.onopen = () => {
      setStatus("connected");
      armStale();
    };

    es.onerror = () => {
      setStatus(es.readyState === EventSource.CLOSED ? "disconnected" : "reconnecting");
    };

    es.onmessage = (event) => {
      let payload: Record<string, PriceUpdate>;
      try {
        payload = JSON.parse(event.data);
      } catch {
        return;
      }
      armStale();
      setState((s) => {
        const firstPrices = { ...s.firstPrices };
        const history = { ...s.history };
        for (const [ticker, u] of Object.entries(payload)) {
          if (firstPrices[ticker] === undefined) firstPrices[ticker] = u.price;
          const prev = history[ticker] ?? [];
          const last = prev[prev.length - 1];
          if (!last || last.time !== u.timestamp) {
            history[ticker] = [...prev, { time: u.timestamp, value: u.price }].slice(-MAX_POINTS);
          }
        }
        return { prices: { ...s.prices, ...payload }, firstPrices, history, status: "connected" };
      });
    };

    return () => {
      clearTimeout(staleTimer);
      es.close();
    };
  }, [url]);

  return state;
}
