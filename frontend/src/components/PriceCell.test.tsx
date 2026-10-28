import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PriceCell } from "./PriceCell";

describe("PriceCell", () => {
  it("flashes green on an uptick and red on a downtick, remounting on each change", () => {
    const { rerender } = render(<PriceCell price={100} direction="flat" testId="p" />);
    const first = screen.getByTestId("p");
    expect(first).toHaveTextContent("100.00");
    expect(first.className).not.toMatch(/flash/);

    rerender(<PriceCell price={101} direction="up" testId="p" />);
    const up = screen.getByTestId("p");
    expect(up).toHaveClass("flash-up");
    expect(up).not.toBe(first); // new element → animation replays

    rerender(<PriceCell price={99.5} direction="down" testId="p" />);
    expect(screen.getByTestId("p")).toHaveClass("flash-down");
  });

  it("shows a placeholder when there is no price yet", () => {
    render(<PriceCell price={null} direction={null} testId="p" />);
    expect(screen.getByTestId("p")).toHaveTextContent("—");
  });
});
