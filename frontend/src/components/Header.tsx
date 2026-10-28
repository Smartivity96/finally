import { fmtSigned, fmtUsd, signClass } from "@/lib/format";
import type { ConnectionStatus } from "@/lib/types";

const STATUS_STYLE: Record<ConnectionStatus, { color: string; label: string }> = {
  connected: { color: "bg-up", label: "Live" },
  reconnecting: { color: "bg-accent pulse-dot", label: "Reconnecting" },
  disconnected: { color: "bg-down", label: "Disconnected" },
};

export function Header({
  totalValue,
  cash,
  pnl,
  status,
  chatOpen,
  onToggleChat,
}: {
  totalValue: number;
  cash: number;
  pnl: number;
  status: ConnectionStatus;
  chatOpen: boolean;
  onToggleChat: () => void;
}) {
  const s = STATUS_STYLE[status];
  return (
    <header className="flex h-14 shrink-0 items-center gap-6 border-b border-line bg-panel px-4">
      <div className="flex items-baseline gap-2">
        <span className="font-display text-xl font-bold tracking-wide text-text">
          Fin<span className="text-accent">Ally</span>
        </span>
        <span className="label hidden sm:inline">AI trading workstation</span>
      </div>

      <div className="ml-auto flex items-center gap-6">
        <Stat label="Portfolio">
          <span data-testid="total-value" className="num text-lg font-semibold text-text">
            {fmtUsd(totalValue)}
          </span>
        </Stat>
        <Stat label="Cash">
          <span data-testid="cash-balance" className="num text-text">
            {fmtUsd(cash)}
          </span>
        </Stat>
        <Stat label="Unrealized">
          <span className={`num ${signClass(pnl)}`}>{fmtSigned(pnl)}</span>
        </Stat>

        <div
          data-testid="connection-status"
          data-status={status}
          title={s.label}
          className="flex items-center gap-2"
        >
          <span className={`h-2 w-2 rounded-full ${s.color}`} />
          <span className="label hidden md:inline">{s.label}</span>
        </div>

        <button
          type="button"
          onClick={onToggleChat}
          aria-pressed={chatOpen}
          className="border border-line px-3 py-1 font-display text-xs font-semibold tracking-widest text-blue uppercase hover:border-blue"
        >
          {chatOpen ? "Hide AI" : "Ask AI"}
        </button>
      </div>
    </header>
  );
}

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col items-end leading-tight">
      <span className="label text-[10px]">{label}</span>
      {children}
    </div>
  );
}
