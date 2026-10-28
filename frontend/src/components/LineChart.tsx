"use client";

import { useEffect, useRef } from "react";
import {
  AreaSeries,
  ColorType,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import { toChartSeries, type Point } from "@/lib/series";

/** Area chart (Lightweight Charts, canvas) that redraws when `points` change. */
export function LineChart({
  points,
  color,
  testId,
}: {
  points: Point[];
  color: string;
  testId: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#7c8899",
        fontFamily: "JetBrains Mono, ui-monospace, monospace",
        fontSize: 10,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "rgba(37, 48, 65, 0.5)" },
        horzLines: { color: "rgba(37, 48, 65, 0.5)" },
      },
      rightPriceScale: { borderColor: "#253041" },
      timeScale: { borderColor: "#253041", timeVisible: true, secondsVisible: true },
      crosshair: { horzLine: { color: "#ecad0a" }, vertLine: { color: "#ecad0a" } },
    });
    seriesRef.current = chart.addSeries(AreaSeries, {
      lineColor: color,
      lineWidth: 2,
      topColor: `${color}55`,
      bottomColor: `${color}00`,
      priceLineColor: color,
    });
    chartRef.current = chart;
    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, [color]);

  useEffect(() => {
    seriesRef.current?.setData(
      toChartSeries(points).map((p) => ({ time: p.time as UTCTimestamp, value: p.value })),
    );
    chartRef.current?.timeScale().fitContent();
  }, [points]);

  return <div ref={ref} data-testid={testId} className="h-full w-full" />;
}
