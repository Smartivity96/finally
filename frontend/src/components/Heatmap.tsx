"use client";

import { useEffect, useRef, useState } from "react";
import { heatColor, squarify, type LivePosition } from "@/lib/calc";
import { fmtPct } from "@/lib/format";
import { Panel } from "./Panel";

export function Heatmap({
  positions,
  onSelect,
}: {
  positions: LivePosition[];
  onSelect: (ticker: string) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      setSize({ w: entry.contentRect.width, h: entry.contentRect.height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const byTicker = new Map(positions.map((p) => [p.ticker, p]));
  const rects = squarify(
    positions.map((p) => ({ key: p.ticker, value: p.value })),
    0,
    0,
    size.w,
    size.h,
  );

  return (
    <Panel title="Positions heatmap" className="h-full">
      <div ref={ref} data-testid="heatmap" className="relative h-full w-full overflow-hidden">
        {positions.length === 0 && (
          <p className="absolute inset-0 grid place-items-center text-sm text-muted">
            Buy a position to see it here, sized by weight.
          </p>
        )}
        {rects.map((r) => {
          const p = byTicker.get(r.key)!;
          const small = r.w < 56 || r.h < 34;
          return (
            <button
              type="button"
              key={r.key}
              data-testid={`heatmap-cell-${r.key}`}
              onClick={() => onSelect(r.key)}
              title={`${r.key} ${fmtPct(p.pnlPercent)}`}
              className="absolute flex flex-col items-start justify-start overflow-hidden border border-ink p-1.5 text-left transition-colors duration-500"
              style={{ left: r.x, top: r.y, width: r.w, height: r.h, background: heatColor(p.pnlPercent) }}
            >
              <span className="font-display text-sm leading-none font-bold text-white">{r.key}</span>
              {!small && <span className="num mt-1 text-[11px] text-white/85">{fmtPct(p.pnlPercent)}</span>}
            </button>
          );
        })}
      </div>
    </Panel>
  );
}
