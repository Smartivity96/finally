import type { LivePosition } from "@/lib/calc";
import { fmtPct, fmtPrice, fmtQty, fmtSigned, signClass } from "@/lib/format";
import { Panel } from "./Panel";

export function PositionsTable({
  positions,
  onSelect,
}: {
  positions: LivePosition[];
  onSelect: (ticker: string) => void;
}) {
  return (
    <Panel title="Positions" className="h-full">
      <div className="h-full overflow-auto">
        <table data-testid="positions-table" className="w-full text-sm">
          <thead className="sticky top-0 bg-panel">
            <tr className="label text-[10px]">
              <th className="px-3 py-1.5 text-left font-semibold">Ticker</th>
              <th className="px-3 py-1.5 text-right font-semibold">Qty</th>
              <th className="px-3 py-1.5 text-right font-semibold">Avg cost</th>
              <th className="px-3 py-1.5 text-right font-semibold">Price</th>
              <th className="px-3 py-1.5 text-right font-semibold">Unrealized P&amp;L</th>
              <th className="px-3 py-1.5 text-right font-semibold">%</th>
            </tr>
          </thead>
          <tbody>
            {positions.length === 0 && (
              <tr>
                <td colSpan={6} className="px-3 py-6 text-center text-muted">
                  No positions yet. Use the trade bar or ask the AI to buy.
                </td>
              </tr>
            )}
            {positions.map((p) => (
              <tr
                key={p.ticker}
                data-testid={`position-row-${p.ticker}`}
                onClick={() => onSelect(p.ticker)}
                className="num cursor-pointer border-t border-line/60 hover:bg-raised"
              >
                <td className="px-3 py-1.5 font-display font-semibold tracking-wide">{p.ticker}</td>
                <td className="px-3 py-1.5 text-right">{fmtQty(p.quantity)}</td>
                <td className="px-3 py-1.5 text-right">{fmtPrice(p.avg_cost)}</td>
                <td className="px-3 py-1.5 text-right">{fmtPrice(p.current_price)}</td>
                <td className={`px-3 py-1.5 text-right ${signClass(p.pnl)}`}>{fmtSigned(p.pnl)}</td>
                <td className={`px-3 py-1.5 text-right ${signClass(p.pnlPercent)}`}>{fmtPct(p.pnlPercent)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
