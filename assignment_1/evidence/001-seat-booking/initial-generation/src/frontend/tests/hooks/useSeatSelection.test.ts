import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { Seat } from "../../src/api/types";
import { useSeatSelection } from "../../src/hooks/useSeatSelection";

function seatList(booked: number[] = []): Seat[] {
  return Array.from({ length: 10 }, (_, index) => ({
    seat_number: index + 1,
    status: booked.includes(index + 1) ? "booked" : "available",
  }));
}

describe("useSeatSelection", () => {
  it("toggles a seat on and off", () => {
    const { result } = renderHook(() => useSeatSelection(seatList()));

    act(() => result.current.toggle(3));
    expect(result.current.selected).toEqual([3]);
    act(() => result.current.toggle(3));
    expect(result.current.selected).toEqual([]);
  });

  it("keeps the selection ordered by seat number", () => {
    const { result } = renderHook(() => useSeatSelection(seatList()));

    act(() => result.current.toggle(5));
    act(() => result.current.toggle(2));

    expect(result.current.selected).toEqual([2, 5]);
  });

  it("cannot select a booked seat", () => {
    const { result } = renderHook(() => useSeatSelection(seatList([4])));

    act(() => result.current.toggle(4));

    expect(result.current.selected).toEqual([]);
  });

  it("ignores a seventh seat and reports the limit", () => {
    const { result } = renderHook(() => useSeatSelection(seatList()));

    for (const seat of [1, 2, 3, 4, 5, 6]) act(() => result.current.toggle(seat));
    expect(result.current.limitReached).toBe(true);
    act(() => result.current.toggle(7));

    expect(result.current.selected).toEqual([1, 2, 3, 4, 5, 6]);
  });

  it("allows deselecting at the limit to free a slot", () => {
    const { result } = renderHook(() => useSeatSelection(seatList()));
    for (const seat of [1, 2, 3, 4, 5, 6]) act(() => result.current.toggle(seat));

    act(() => result.current.toggle(1));

    expect(result.current.limitReached).toBe(false);
    expect(result.current.selected).toEqual([2, 3, 4, 5, 6]);
  });

  it("clears the selection", () => {
    const { result } = renderHook(() => useSeatSelection(seatList()));
    act(() => result.current.toggle(1));
    act(() => result.current.toggle(2));

    act(() => result.current.clear());

    expect(result.current.selected).toEqual([]);
  });

  it("drops seats that become booked", () => {
    const { result, rerender } = renderHook(({ seats }) => useSeatSelection(seats), {
      initialProps: { seats: seatList() },
    });
    act(() => result.current.toggle(3));
    act(() => result.current.toggle(4));

    rerender({ seats: seatList([3]) });

    expect(result.current.selected).toEqual([4]);
  });
});
