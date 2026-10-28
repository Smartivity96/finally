import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ChatPanel, type ChatMessage } from "./ChatPanel";

const noop = () => {};

describe("ChatPanel", () => {
  it("shows the loading indicator only while waiting", () => {
    const { rerender } = render(<ChatPanel messages={[]} loading onSend={noop} onClose={noop} />);
    expect(screen.getByTestId("chat-loading")).toBeInTheDocument();
    rerender(<ChatPanel messages={[]} loading={false} onSend={noop} onClose={noop} />);
    expect(screen.queryByTestId("chat-loading")).not.toBeInTheDocument();
  });

  it("renders messages with inline executed and failed actions", () => {
    const messages: ChatMessage[] = [
      { role: "user", content: "Buy 5 NVDA" },
      {
        role: "assistant",
        content: "Done.",
        trades: [
          { ticker: "NVDA", side: "buy", quantity: 5, price: 875.2, status: "executed" },
          { ticker: "TSLA", side: "buy", quantity: 1000, price: null, status: "failed", error: "Insufficient cash" },
        ],
        watchlist_changes: [{ ticker: "PYPL", action: "add", status: "executed" }],
      },
    ];
    render(<ChatPanel messages={messages} loading={false} onSend={noop} onClose={noop} />);
    expect(screen.getAllByTestId("chat-message")).toHaveLength(2);
    const actions = screen.getAllByTestId("chat-action").map((a) => a.textContent);
    expect(actions).toEqual([
      "✓ Added PYPL to watchlist",
      "✓ Bought 5 NVDA @ 875.20",
      "✗ Buy 1,000 TSLA failed: Insufficient cash",
    ]);
  });

  it("sends the trimmed message and clears the input", () => {
    const onSend = vi.fn();
    render(<ChatPanel messages={[]} loading={false} onSend={onSend} onClose={noop} />);
    const input = screen.getByTestId("chat-input");
    fireEvent.change(input, { target: { value: "  hello  " } });
    fireEvent.click(screen.getByTestId("chat-send"));
    expect(onSend).toHaveBeenCalledWith("hello");
    expect(input).toHaveValue("");
  });
});
