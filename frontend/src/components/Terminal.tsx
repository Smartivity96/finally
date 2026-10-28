"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { usePriceStream } from "@/hooks/usePriceStream";
import { api } from "@/lib/api";
import { livePositions, portfolioValue } from "@/lib/calc";
import type { Portfolio, Side, Snapshot, WatchlistItem } from "@/lib/types";
import { ChatPanel, fromChatResponse, type ChatMessage } from "./ChatPanel";
import { Header } from "./Header";
import { Heatmap } from "./Heatmap";
import { MainChart } from "./MainChart";
import { PnlChart } from "./PnlChart";
import { PositionsTable } from "./PositionsTable";
import { TradeBar } from "./TradeBar";
import { Watchlist } from "./Watchlist";

const HISTORY_POLL_MS = 30_000;

export function Terminal() {
  const stream = usePriceStream();
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [tradeTicker, setTradeTicker] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatOpen, setChatOpen] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const refreshPortfolio = useCallback(async () => {
    const [p, h] = await Promise.all([api.portfolio(), api.history()]);
    setPortfolio(p);
    setSnapshots(h);
  }, []);

  const refreshWatchlist = useCallback(async () => {
    const w = await api.watchlist();
    setWatchlist(w);
    setSelected((cur) => cur ?? w[0]?.ticker ?? null);
  }, []);

  useEffect(() => {
    Promise.all([refreshPortfolio(), refreshWatchlist()])
      .then(() => setLoadError(null))
      .catch((e) => setLoadError((e as Error).message));
    api
      .chatHistory()
      .then((h) =>
        setMessages(
          h.map((m) => ({
            role: m.role,
            content: m.content,
            trades: m.actions?.trades,
            watchlist_changes: m.actions?.watchlist_changes,
          })),
        ),
      )
      .catch(() => {});
    const id = setInterval(() => {
      api.history().then(setSnapshots).catch(() => {});
    }, HISTORY_POLL_MS);
    return () => clearInterval(id);
  }, [refreshPortfolio, refreshWatchlist]);

  const select = (ticker: string) => {
    setSelected(ticker);
    setTradeTicker(ticker);
  };

  const positions = useMemo(
    () => livePositions(portfolio?.positions ?? [], stream.prices),
    [portfolio, stream.prices],
  );
  const cash = portfolio?.cash_balance ?? 0;
  const total = portfolio ? portfolioValue(cash, portfolio.positions, stream.prices) : 0;
  const pnl = positions.reduce((s, p) => s + p.pnl, 0);

  const trade = async (ticker: string, quantity: number, side: Side) => {
    const res = await api.trade(ticker, quantity, side);
    setPortfolio(res.portfolio);
    api.history().then(setSnapshots).catch(() => {});
  };

  const addTicker = async (ticker: string) => {
    await api.addTicker(ticker);
    await refreshWatchlist();
  };

  const removeTicker = async (ticker: string) => {
    await api.removeTicker(ticker);
    setSelected((cur) => (cur === ticker ? null : cur));
    await refreshWatchlist();
  };

  const sendChat = async (text: string) => {
    setMessages((m) => [...m, { role: "user", content: text }]);
    setChatLoading(true);
    try {
      const res = await api.chat(text);
      setMessages((m) => [...m, fromChatResponse(res)]);
      if (res.trades.length || res.watchlist_changes.length) {
        await Promise.all([refreshPortfolio(), refreshWatchlist()]);
      }
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: `Couldn't reach the assistant: ${(e as Error).message}` },
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <div className="flex h-screen min-h-0 flex-col">
      <Header
        totalValue={total}
        cash={cash}
        pnl={pnl}
        status={stream.status}
        chatOpen={chatOpen}
        onToggleChat={() => setChatOpen((o) => !o)}
      />
      {loadError && (
        <p className="border-b border-down/40 bg-down/10 px-4 py-1 text-sm text-down">
          Can&apos;t load portfolio data: {loadError}. Check that the server is running, then reload.
        </p>
      )}

      <main
        className={`grid min-h-0 flex-1 grid-cols-1 content-start gap-1 overflow-auto p-1 lg:content-stretch lg:overflow-hidden ${
          chatOpen ? "lg:grid-cols-[280px_1fr_360px]" : "lg:grid-cols-[280px_1fr]"
        }`}
      >
        <div className="h-[420px] min-h-0 lg:h-auto">
          <Watchlist
            items={watchlist}
            stream={stream}
            selected={selected}
            onSelect={select}
            onAdd={addTicker}
            onRemove={removeTicker}
          />
        </div>

        <div className="grid h-[1100px] min-h-0 min-w-0 grid-rows-[minmax(280px,1.3fr)_auto_minmax(220px,1fr)_minmax(160px,0.8fr)] gap-1 lg:h-auto">
          <MainChart ticker={selected} stream={stream} />
          <TradeBar ticker={tradeTicker} onTickerChange={setTradeTicker} onTrade={trade} />
          <div className="grid min-h-0 gap-1 md:grid-cols-2">
            <Heatmap positions={positions} onSelect={select} />
            <PnlChart snapshots={snapshots} />
          </div>
          <PositionsTable positions={positions} onSelect={select} />
        </div>

        {chatOpen && (
          <div className="h-[520px] min-h-0 lg:h-auto">
            <ChatPanel
              messages={messages}
              loading={chatLoading}
              onSend={sendChat}
              onClose={() => setChatOpen(false)}
            />
          </div>
        )}
      </main>
    </div>
  );
}
