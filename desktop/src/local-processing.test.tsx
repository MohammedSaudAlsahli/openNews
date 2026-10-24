// @vitest-environment jsdom
import React from "react";
import { afterEach, expect, it, vi } from "vitest";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { call } from "./engine";
import { LocalProcessing } from "./local-processing";

vi.mock("./engine", () => ({ call: vi.fn() }));
const policy = {
  mode: "quiet",
  index_on_battery: false,
  paused: false,
  phase: "ready",
};
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  vi.useRealTimers();
});

it("disables unavailable preferences and recovers a failed initial read", async () => {
  vi.mocked(call).mockRejectedValueOnce(new Error("Connection lost"));
  render(<LocalProcessing />);
  expect((screen.getByRole("combobox") as HTMLSelectElement).disabled).toBe(
    true,
  );
  await screen.findByRole("alert");
  vi.mocked(call).mockResolvedValue(policy);
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await waitFor(() =>
    expect((screen.getByRole("combobox") as HTMLSelectElement).disabled).toBe(
      false,
    ),
  );
  expect(screen.queryByRole("alert")).toBeNull();
});

it("retains the saved preference after a failed write and allows another attempt", async () => {
  vi.mocked(call).mockResolvedValue(policy);
  render(<LocalProcessing />);
  const select = screen.getByRole("combobox") as HTMLSelectElement;
  await waitFor(() => expect(select.disabled).toBe(false));
  vi.mocked(call).mockRejectedValueOnce(new Error("Could not save"));
  fireEvent.change(select, { target: { value: "balanced" } });
  await screen.findByRole("alert");
  expect(select.value).toBe("quiet");
  expect(select.disabled).toBe(false);
  vi.mocked(call).mockResolvedValue({ ...policy, mode: "balanced" });
  fireEvent.change(select, { target: { value: "balanced" } });
  await screen.findByText("Saved");
  expect(select.value).toBe("balanced");
  expect(call).toHaveBeenLastCalledWith("news.local.policy.set", {
    mode: "balanced",
  });
});

it("ignores a stale poll after an acknowledged preference change", async () => {
  vi.useFakeTimers();
  Object.defineProperty(document, "visibilityState", {
    configurable: true,
    value: "visible",
  });
  vi.mocked(call).mockResolvedValue(policy);
  render(<LocalProcessing />);
  await act(async () => {});
  let finish!: (value: object) => void;
  vi.mocked(call).mockImplementationOnce(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
  );
  await act(async () => vi.advanceTimersByTime(5000));
  vi.mocked(call).mockResolvedValue({ ...policy, mode: "balanced" });
  fireEvent.change(screen.getByRole("combobox"), {
    target: { value: "balanced" },
  });
  await act(async () => {});
  await act(async () => finish(policy));
  expect((screen.getByRole("combobox") as HTMLSelectElement).value).toBe(
    "balanced",
  );
});

it("distinguishes an acknowledged stop request from a fully stopped task", async () => {
  vi.mocked(call).mockResolvedValue(policy);
  render(<LocalProcessing />);
  await waitFor(() =>
    expect(
      (screen.getByRole("button", { name: "Pause" }) as HTMLButtonElement)
        .disabled,
    ).toBe(false),
  );
  vi.mocked(call).mockResolvedValue({
    ...policy,
    paused: true,
    phase: "stopping",
  });
  fireEvent.click(screen.getByRole("button", { name: "Pause" }));
  await screen.findByText("Stopping background processing…");
  expect(
    (screen.getByRole("button", { name: "Resume" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  expect(call).toHaveBeenLastCalledWith("news.local.policy.set", {
    paused: true,
  });
});

it("does not overlap slow polls or keep polling an unmounted panel", async () => {
  vi.useFakeTimers();
  vi.mocked(call).mockImplementation(() => new Promise(() => {}));
  const { unmount } = render(<LocalProcessing />);
  await act(async () => vi.advanceTimersByTime(20000));
  expect(call).toHaveBeenCalledTimes(1);
  unmount();
  await act(async () => vi.advanceTimersByTime(20000));
  expect(call).toHaveBeenCalledTimes(1);
});
