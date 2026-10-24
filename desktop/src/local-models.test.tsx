// @vitest-environment jsdom
import React from "react";
import { afterEach, expect, it, vi } from "vitest";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { call } from "./engine";
import { LocalModels } from "./local-models";

vi.mock("./engine", () => ({ call: vi.fn() }));
vi.mock("./model-library", () => ({
  ModelLibrary: () => <div>Model library</div>,
}));
vi.mock("./local-processing", () => ({ LocalProcessing: () => null }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  vi.useRealTimers();
});

it("waits for actual connection results before displaying readiness", async () => {
  let finish!: (result: object) => void;
  vi.mocked(call).mockImplementation(async (command) => {
    if (command === "news.local.status")
      return new Promise((resolve) => {
        finish = resolve;
      });
    return command === "news.digest.status"
      ? { local_model: "summary:2b" }
      : { model: "embedding:270m" };
  });
  render(<LocalModels onError={vi.fn()} />);
  expect(screen.getByText("Checking connection…").getAttribute("role")).toBe(
    "status",
  );
  expect(screen.queryByText("Not running")).toBeNull();
  await act(async () => finish({ runtime: true }));
  expect(screen.getByText("Ready").getAttribute("role")).toBe("status");
  expect(screen.getAllByText("summary:2b").length).toBe(1);
  expect(screen.getAllByText("Model library")).toHaveLength(1);
  fireEvent.click(screen.getByRole("button", { name: /Article search/ }));
  expect(screen.getAllByText("embedding:270m").length).toBe(1);
  expect(screen.getByText("Model library")).toBeTruthy();
  expect(
    screen
      .getByRole("button", { name: /Article search/ })
      .getAttribute("aria-pressed"),
  ).toBe("true");
});

it("shows failed verification separately from stopped Ollama and can retry", async () => {
  const outerError = vi.fn();
  vi.mocked(call).mockRejectedValue(new Error("Network offline"));
  render(<LocalModels onError={outerError} />);
  await screen.findByText("Could not verify");
  expect(screen.getByRole("alert").textContent).toContain("Network offline");
  expect(screen.queryByText("Not running")).toBeNull();
  expect(outerError).not.toHaveBeenCalled();
  vi.mocked(call).mockResolvedValue({ runtime: true });
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  await screen.findByText("Ready");
  expect(screen.queryByRole("alert")).toBeNull();
});

it("does not overlap slow connection polls and stops polling on unmount", async () => {
  vi.useFakeTimers();
  Object.defineProperty(document, "visibilityState", {
    configurable: true,
    value: "visible",
  });
  vi.mocked(call).mockImplementation(() => new Promise(() => {}));
  const { unmount } = render(<LocalModels onError={vi.fn()} />);
  expect(call).toHaveBeenCalledTimes(3);
  await act(async () => vi.advanceTimersByTime(20000));
  expect(call).toHaveBeenCalledTimes(3);
  unmount();
  await act(async () => vi.advanceTimersByTime(20000));
  expect(call).toHaveBeenCalledTimes(3);
});
