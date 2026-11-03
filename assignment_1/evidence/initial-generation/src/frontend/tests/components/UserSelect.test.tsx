import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../../src/api/errors";
import type { Page, User } from "../../src/api/types";
import { UserSelect } from "../../src/components/UserSelect";
import type { AsyncResource } from "../../src/hooks/useAsyncResource";
import { makeUsers, page } from "../helpers";

type Users = AsyncResource<Page<User>>;

function ready(items: User[]): Users {
  return { status: "ready", data: page(items), refresh: vi.fn() };
}

describe("UserSelect", () => {
  it("is a labelled select with a placeholder and every user", () => {
    render(<UserSelect users={ready(makeUsers())} value={null} onChange={vi.fn()} />);

    const select = screen.getByLabelText("Booking as");
    expect(select).toHaveValue("");
    const options = screen.getAllByRole("option").map((option) => option.textContent);
    expect(options).toEqual(["Choose a user", "Asha", "Ravi", "Meera"]);
  });

  it("reports the chosen user id, and null for the placeholder", async () => {
    const onChange = vi.fn();
    render(<UserSelect users={ready(makeUsers())} value={null} onChange={onChange} />);
    const select = screen.getByLabelText("Booking as");

    await userEvent.selectOptions(select, "Ravi");
    expect(onChange).toHaveBeenLastCalledWith(2);
    await userEvent.selectOptions(select, "Choose a user");
    expect(onChange).toHaveBeenLastCalledWith(null);
  });

  it("shows the selected user", () => {
    render(<UserSelect users={ready(makeUsers())} value={2} onChange={vi.fn()} />);

    expect(screen.getByLabelText("Booking as")).toHaveValue("2");
  });

  it("shows loading and empty states", () => {
    const { rerender } = render(
      <UserSelect users={{ status: "loading", refresh: vi.fn() }} value={null} onChange={vi.fn()} />,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Loading users");

    rerender(<UserSelect users={ready([])} value={null} onChange={vi.fn()} />);
    expect(screen.getByRole("status")).toHaveTextContent("No users available");
  });

  it("shows an error with a working Retry", async () => {
    const refresh = vi.fn();
    const error = new ApiError("unavailable", 503, "service_unavailable", "down");
    render(<UserSelect users={{ status: "error", error, refresh }} value={null} onChange={vi.fn()} />);

    expect(screen.getByRole("alert")).toHaveTextContent("Service unavailable");
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(refresh).toHaveBeenCalledOnce();
  });
});
