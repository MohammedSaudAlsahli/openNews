// @vitest-environment jsdom
import React from "react";
import { afterEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { Markdown } from "./components";

vi.mock("./highlighted-code", () => ({
  default: () => {
    throw new Error("Optional highlighter could not load");
  },
}));
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("retains readable and copyable code if optional highlighting fails", async () => {
  vi.spyOn(console, "error").mockImplementation(() => {});
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: { writeText },
  });
  const { container, rerender } = render(
    <Markdown
      text={"# Article\n\n```python\nprint(42)\n```\n\nStill readable."}
    />,
  );
  await waitFor(() =>
    expect(container.querySelector("pre code")?.textContent).toBe(
      "print(42)\n",
    ),
  );
  expect(screen.getByRole("heading", { name: "Article" })).toBeTruthy();
  expect(screen.getByText("Still readable.")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Copy code" }));
  await screen.findByText("Copied");
  expect(writeText).toHaveBeenCalledWith("print(42)\n");
  rerender(<Markdown text={"```python\nprint(43)\n```"} />);
  expect(container.querySelector("pre code")?.textContent).toBe("print(43)\n");
});
