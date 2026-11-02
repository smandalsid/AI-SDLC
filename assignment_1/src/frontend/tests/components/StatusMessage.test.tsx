import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { StatusMessage } from "../../src/components/StatusMessage";

describe("StatusMessage", () => {
  it.each(["loading", "empty", "success"] as const)("announces %s politely", (variant) => {
    render(<StatusMessage variant={variant} message="Hello there" />);

    expect(screen.getByRole("status")).toHaveTextContent("Hello there");
  });

  it.each(["error", "conflict"] as const)("announces %s as an alert", (variant) => {
    render(<StatusMessage variant={variant} message="Something failed" />);

    expect(screen.getByRole("alert")).toHaveTextContent("Something failed");
  });

  it("offers Retry on an error and calls the handler", async () => {
    const onRetry = vi.fn();
    render(<StatusMessage variant="error" message="Failed" onRetry={onRetry} />);

    await userEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("shows no Retry button without a handler", () => {
    render(<StatusMessage variant="error" message="Failed" />);

    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
  });
});
