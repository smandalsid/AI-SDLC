import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { BusList } from "../../src/components/BusList";
import type { Bus } from "../../src/api/types";

const buses: Bus[] = [
  { id: 1, name: "Bus A", total_seats: 20 },
  { id: 2, name: "Bus B", total_seats: 30 },
];

describe("BusList", () => {
  it("renders each bus name and seat count as a link to its seat page", () => {
    render(
      <MemoryRouter>
        <BusList buses={buses} />
      </MemoryRouter>,
    );

    const first = screen.getByRole("link", { name: /Bus A/ });
    expect(first).toHaveAttribute("href", "/buses/1");
    expect(first).toHaveTextContent("20 seats");
    const second = screen.getByRole("link", { name: /Bus B/ });
    expect(second).toHaveAttribute("href", "/buses/2");
    expect(second).toHaveTextContent("30 seats");
  });
});
