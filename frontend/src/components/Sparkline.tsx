import type { PricePoint } from "@/hooks/usePriceStream";

/** Tiny inline-SVG polyline of prices since page load. */
export function Sparkline({
  points,
  width = 80,
  height = 22,
}: {
  points: PricePoint[] | undefined;
  width?: number;
  height?: number;
}) {
  if (!points || points.length < 2) {
    return <svg width={width} height={height} aria-hidden />;
  }
  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const step = width / (values.length - 1);
  const d = values
    .map((v, i) => `${(i * step).toFixed(1)},${(height - 1 - ((v - min) / range) * (height - 2)).toFixed(1)}`)
    .join(" ");
  const up = values[values.length - 1] >= values[0];
  return (
    <svg width={width} height={height} aria-hidden className="block">
      <polyline
        points={d}
        fill="none"
        strokeWidth={1.25}
        stroke={up ? "var(--color-up)" : "var(--color-down)"}
        strokeLinejoin="round"
      />
    </svg>
  );
}
