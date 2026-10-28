"use client";

import { useMemo } from "react";
import type { Snapshot } from "@/lib/types";
import { LineChart } from "./LineChart";
import { Panel } from "./Panel";

export function PnlChart({ snapshots }: { snapshots: Snapshot[] }) {
  const points = useMemo(
    () => snapshots.map((s) => ({ time: Date.parse(s.recorded_at) / 1000, value: s.total_value })),
    [snapshots],
  );
  return (
    <Panel title="Portfolio value" className="h-full">
      <div className="h-full p-1">
        <LineChart points={points} color="#ecad0a" testId="pnl-chart" />
      </div>
    </Panel>
  );
}
