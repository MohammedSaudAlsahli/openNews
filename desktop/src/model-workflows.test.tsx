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
import { ModelLibrary } from "./model-library";
import { IndexDetails } from "./index-details";
import { call } from "./engine";

vi.mock("./engine", () => ({ call: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
const model = { id: "small:1b", name: "Small model" };
const idle = { models: [model], download: { phase: "idle" } };
const capacity = {
  size: 1e9,
  free_disk: 1e11,
  required_disk: 3e9,
  estimated_memory: 2e9,
  fit: "fits",
  can_download: true,
};

it("retries a failed local model search without claiming there are no matches", async () => {
  let attempts = 0;
  vi.mocked(call).mockImplementation(async (command) => {
    if (command === "news.local.search") {
      if (++attempts === 1) throw new Error("Library unreachable");
      return { models: [model] };
    }
    return idle;
  });
  const error = vi.fn();
  render(<ModelLibrary onError={error} />);
  fireEvent.click(screen.getByRole("button", { name: "Ollama library" }));
  await screen.findByText("Library unreachable");
  expect(screen.queryByText("No models match your search.")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(
    await screen.findByRole("button", { name: /Small model/ }),
  ).toBeTruthy();
  expect(error).not.toHaveBeenCalled();
});

it("keeps the chosen model selected and retries a failed capacity inspection", async () => {
  let attempts = 0;
  vi.mocked(call).mockImplementation(async (command) => {
    if (command === "news.local.inspect") {
      if (++attempts === 1) throw new Error("Size service unavailable");
      return capacity;
    }
    return idle;
  });
  render(<ModelLibrary onError={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: /Small model/ }));
  await screen.findByText("Size service unavailable");
  expect(
    screen
      .getByRole("button", { name: /Small model/ })
      .getAttribute("aria-pressed"),
  ).toBe("true");
  expect(screen.queryByRole("button", { name: "Download and use" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(await screen.findByText("Estimated to fit your Mac")).toBeTruthy();
  expect(
    (
      screen.getByRole("button", {
        name: "Download and use",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(false);
});

it("acknowledges a download immediately and locks cancellation while it is pending", async () => {
  let cancel: (result: unknown) => void = () => {};
  let started = false;
  vi.mocked(call).mockImplementation(async (command) => {
    if (command === "news.local.inspect") return capacity;
    if (command === "news.local.download") {
      started = true;
      return {
        download: {
          phase: "checking",
          model: model.id,
          completed: 0,
          total: 1e9,
        },
      };
    }
    if (command === "news.local.cancel")
      return new Promise((resolve) => {
        cancel = resolve;
      });
    // A slow follow-up status must not delay acknowledgement of accepted work.
    if (command === "news.local.status" && started)
      return new Promise(() => {});
    return idle;
  });
  render(<ModelLibrary onError={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: /Small model/ }));
  fireEvent.click(
    await screen.findByRole("button", { name: "Download and use" }),
  );
  await screen.findByText("Checking requirements…");
  expect(screen.getByRole("progressbar").getAttribute("value")).toBe("0");
  fireEvent.click(screen.getByRole("button", { name: "Cancel download" }));
  fireEvent.click(screen.getByRole("button", { name: "Stopping…" }));
  expect(
    vi
      .mocked(call)
      .mock.calls.filter(([command]) => command === "news.local.cancel"),
  ).toHaveLength(1);
  await act(async () =>
    cancel({ download: { phase: "cancelled", model: model.id } }),
  );
  expect(await screen.findByText("Download cancelled")).toBeTruthy();
});

it("ignores sizes returned for a model selected before a newer one", async () => {
  let old: (result: unknown) => void = () => {};
  vi.mocked(call).mockImplementation(async (command, payload) => {
    if (command === "news.local.variants")
      return payload?.model === "older"
        ? new Promise((resolve) => {
            old = resolve;
          })
        : { variants: [{ id: "current:2b" }] };
    if (command === "news.local.inspect") return capacity;
    return {
      ...idle,
      models: [
        { id: "older", name: "Older model" },
        { id: "current", name: "Current model" },
      ],
    };
  });
  render(<ModelLibrary onError={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: /Older model/ }));
  fireEvent.click(screen.getByRole("button", { name: /Current model/ }));
  await screen.findByRole("option", { name: "current:2b" });
  await act(async () => old({ variants: [{ id: "older:1b" }] }));
  expect(screen.queryByRole("option", { name: "older:1b" })).toBeNull();
  expect(
    (screen.getByRole("combobox", { name: "Model size" }) as HTMLSelectElement)
      .value,
  ).toBe("current:2b");
});

it("loads index details on demand and recovers locally from a failed read", async () => {
  vi.mocked(call)
    .mockRejectedValueOnce(new Error("Index temporarily unavailable"))
    .mockResolvedValue({
      articles: [
        { id: "a1", title: "Indexed story", segments: 4, embedded: 3 },
      ],
    });
  render(<IndexDetails />);
  expect(call).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText("Index details"));
  await screen.findByText("Index temporarily unavailable");
  expect(screen.queryByText("No articles have been indexed yet.")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByText("Indexed story");
  await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
  expect(screen.getByText("4")).toBeTruthy();
  expect(screen.getByText("3")).toBeTruthy();
});

it("shares downloaded models across roles and keeps local filtering and selection when the task changes", async () => {
  const inventory = [
    { id: "search:small", capabilities: ["embedding"], size: 1e8 },
    { id: "writer:small", capabilities: ["completion"], size: 1e9 },
  ];
  vi.mocked(call).mockImplementation(async (command) => {
    if (command === "news.local.available") return { installed: inventory };
    if (command === "news.local.inspect")
      return { ...capacity, capabilities: ["embedding"] };
    return idle;
  });
  const { rerender } = render(
    <ModelLibrary onError={vi.fn()} initialTab="installed" embedding />,
  );
  fireEvent.click(await screen.findByRole("button", { name: /search:small/ }));
  expect(
    await screen.findByRole("button", { name: "Use this model" }),
  ).toBeTruthy();
  fireEvent.change(screen.getByRole("searchbox", { name: "Search models" }), {
    target: { value: "search" },
  });
  expect(screen.queryByRole("button", { name: /writer:small/ })).toBeNull();
  const requests = vi
    .mocked(call)
    .mock.calls.filter(
      ([command]) => command === "news.local.available",
    ).length;
  rerender(
    <ModelLibrary onError={vi.fn()} initialTab="installed" embedding={false} />,
  );
  expect((screen.getByRole("searchbox") as HTMLInputElement).value).toBe(
    "search",
  );
  expect(
    screen
      .getByRole("button", { name: /search:small/ })
      .getAttribute("aria-pressed"),
  ).toBe("true");
  expect(
    (
      screen.getByRole("button", {
        name: "Use this model",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  expect(screen.getByText(/This model creates embeddings/)).toBeTruthy();
  expect(
    vi
      .mocked(call)
      .mock.calls.filter(([command]) => command === "news.local.available"),
  ).toHaveLength(requests);
  fireEvent.click(screen.getByRole("button", { name: "Clear model search" }));
  expect(screen.getByRole("button", { name: /writer:small/ })).toBeTruthy();
  expect(document.activeElement).toBe(screen.getByRole("searchbox"));
  expect(call).toHaveBeenCalledWith("news.local.available", { capability: "" });
});
