"use client";

import { useEffect, useRef, useState } from "react";
import { fmtPrice, fmtQty } from "@/lib/format";
import type { ChatResponse, ChatTrade, ChatWatchlistChange } from "@/lib/types";

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  trades?: ChatTrade[];
  watchlist_changes?: ChatWatchlistChange[];
}

export function ChatPanel({
  messages,
  loading,
  onSend,
  onClose,
}: {
  messages: ChatMessage[];
  loading: boolean;
  onSend: (message: string) => void;
  onClose: () => void;
}) {
  const [input, setInput] = useState("");
  const listRef = useRef<HTMLDivElement>(null);

  // Scroll only the message list (scrollIntoView would also scroll the page on narrow screens)
  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;
    onSend(text);
    setInput("");
  };

  return (
    <aside className="flex h-full min-h-0 flex-col border border-line bg-panel">
      <header className="flex h-8 shrink-0 items-center justify-between border-b border-line px-3">
        <h2 className="label">
          <span className="text-blue">AI</span> copilot
        </h2>
        <button type="button" onClick={onClose} aria-label="Close chat" className="text-xs text-muted hover:text-text">
          ✕
        </button>
      </header>

      <div ref={listRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto p-3">
        {messages.length === 0 && !loading && (
          <p className="text-sm text-muted">
            Ask about your portfolio, or tell me to trade — e.g. “Buy 5 NVDA” or “What’s my biggest risk?”
          </p>
        )}
        {messages.map((m, i) => (
          <Message key={i} message={m} />
        ))}
        {loading && (
          <div data-testid="chat-loading" role="status" className="flex items-center gap-1.5 text-sm text-muted">
            <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-blue" />
            <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-blue [animation-delay:200ms]" />
            <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-blue [animation-delay:400ms]" />
            <span className="ml-1">Thinking…</span>
          </div>
        )}
      </div>

      <form onSubmit={submit} className="flex gap-2 border-t border-line p-2">
        <input
          data-testid="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message FinAlly"
          aria-label="Message"
          className="min-w-0 flex-1 border border-line bg-ink px-2 py-1.5 text-sm placeholder:text-muted focus:border-blue focus:outline-none"
        />
        <button
          data-testid="chat-send"
          type="submit"
          disabled={loading || !input.trim()}
          className="bg-purple px-3 py-1.5 text-sm font-semibold text-white hover:brightness-125 disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </aside>
  );
}

function Message({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const actions = [
    ...(message.watchlist_changes ?? []).map((w) => ({
      ok: w.status === "executed",
      text: `${w.action === "add" ? "Added" : "Removed"} ${w.ticker} ${w.action === "add" ? "to" : "from"} watchlist`,
      failText: `Couldn't ${w.action} ${w.ticker}`,
      error: w.error,
    })),
    ...(message.trades ?? []).map((t) => ({
      ok: t.status === "executed",
      text: `${t.side === "buy" ? "Bought" : "Sold"} ${fmtQty(t.quantity)} ${t.ticker}${t.price != null ? ` @ ${fmtPrice(t.price)}` : ""}`,
      failText: `${t.side === "buy" ? "Buy" : "Sell"} ${fmtQty(t.quantity)} ${t.ticker} failed`,
      error: t.error,
    })),
  ];

  return (
    <div data-testid="chat-message" data-role={message.role} className={isUser ? "flex justify-end" : ""}>
      <div
        className={
          isUser
            ? "max-w-[85%] border border-line bg-raised px-3 py-2 text-sm"
            : "border-l-2 border-blue pl-3 text-sm leading-relaxed"
        }
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {actions.length > 0 && (
          <ul className="mt-2 space-y-1">
            {actions.map((a, i) => (
              <li
                key={i}
                data-testid="chat-action"
                className={`num border px-2 py-1 text-xs ${a.ok ? "border-up/40 text-up" : "border-down/40 text-down"}`}
              >
                {a.ok ? `✓ ${a.text}` : `✗ ${a.failText}${a.error ? `: ${a.error}` : ""}`}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export function fromChatResponse(r: ChatResponse): ChatMessage {
  return { role: "assistant", content: r.message, trades: r.trades, watchlist_changes: r.watchlist_changes };
}
