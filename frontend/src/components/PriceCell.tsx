import { fmtPrice } from "@/lib/format";
import type { Direction } from "@/lib/types";

/**
 * Price that flashes green/red when it changes. Keyed on the price so the
 * span remounts on every change and the CSS animation replays.
 */
export function PriceCell({
  price,
  direction,
  testId,
  className = "",
}: {
  price: number | null | undefined;
  direction: Direction | null | undefined;
  testId?: string;
  className?: string;
}) {
  if (price == null) {
    return (
      <span data-testid={testId} className={`num text-muted ${className}`}>
        —
      </span>
    );
  }
  const flash = direction === "up" ? "flash-up" : direction === "down" ? "flash-down" : "";
  return (
    <span key={price} data-testid={testId} className={`num rounded-sm px-1 ${flash} ${className}`}>
      {fmtPrice(price)}
    </span>
  );
}
