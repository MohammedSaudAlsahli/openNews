// @vitest-environment jsdom
import React from "react";
import { beforeEach, afterEach, expect, it, vi } from "vitest";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { call } from "./engine";
import { SupportPanel } from "./support-panel";
import { TaskInstructions } from "./task-instructions";
import { ActivityPage } from "./activity-page";
import { Updates } from "./updates";
import Settings from "./settings";

vi.mock("./engine", async (original) => ({
  ...(await original<typeof import("./engine")>()),
  call: vi.fn(),
}));
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
vi.mock("@tauri-apps/api/event", () => ({ listen: vi.fn() }));
const originalShowModal = Object.getOwnPropertyDescriptor(
  HTMLDialogElement.prototype,
  "showModal",
);
beforeEach(() => {
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
    configurable: true,
    value: function (this: HTMLDialogElement) {
      this.open = true;
    },
  });
  vi.mocked(listen).mockResolvedValue(vi.fn());
});
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  vi.restoreAllMocks();
  sessionStorage.clear();
  if (originalShowModal)
    Object.defineProperty(
      HTMLDialogElement.prototype,
      "showModal",
      originalShowModal,
    );
  else Reflect.deleteProperty(HTMLDialogElement.prototype, "showModal");
});

it("recovers a failed diagnostic read inside the modal before allowing export", async () => {
  vi.mocked(invoke)
    .mockRejectedValueOnce(new Error("Log unavailable"))
    .mockResolvedValue("safe event");
  render(<SupportPanel onClose={vi.fn()} onError={vi.fn()} />);
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    "Log unavailableTry again",
  );
  expect(
    (
      screen.getByRole("button", {
        name: "Save diagnostic report",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  await screen.findByText("safe event");
  expect(
    (
      screen.getByRole("button", {
        name: "Save diagnostic report",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(false);
});

it("exports the reviewed article context and honors opt-out for the GitHub draft", async () => {
  vi.mocked(invoke).mockImplementation(async (command) =>
    command === "diagnostics_report" ? "safe diagnostic" : "/tmp/report.txt",
  );
  const article = {
    title: "Useful article",
    url: "https://example.com/story?token=secret#private",
    source: "Publisher",
    articleId: "a1",
    stage: "local_cache",
    elapsedMs: 120,
    bodyStatus: "full",
  };
  render(
    <SupportPanel
      article={article}
      incidentCode="ARTICLE_READING_PROBLEM"
      onClose={vi.fn()}
      onError={vi.fn()}
    />,
  );
  await screen.findByText(/safe diagnostic/);
  fireEvent.click(
    screen.getByRole("button", { name: "Save diagnostic report" }),
  );
  await screen.findByText("/tmp/report.txt");
  const exported = vi
    .mocked(invoke)
    .mock.calls.find(([command]) => command === "export_diagnostics")![1] as {
    content: string;
  };
  expect(exported.content).toContain("Useful article");
  expect(exported.content).toContain("https://example.com/story");
  expect(exported.content).toContain("Incident: ARTICLE_READING_PROBLEM");
  expect(exported.content).not.toContain("secret");
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(
    screen.getByRole("button", { name: "Report a problem on GitHub" }),
  );
  await waitFor(() =>
    expect(invoke).toHaveBeenCalledWith("open_external", expect.anything()),
  );
  const address = (
    vi
      .mocked(invoke)
      .mock.calls.find(([command]) => command === "open_external")![1] as {
      address: string;
    }
  ).address;
  expect(new URL(address).searchParams.get("body")).not.toContain(
    "Useful article",
  );
  expect(new URL(address).searchParams.get("body")).toContain(
    "safe diagnostic",
  );
});

it("keeps export errors visible in the modal and permits retry", async () => {
  vi.mocked(invoke).mockImplementation(async (command) => {
    if (command === "export_diagnostics") throw new Error("Disk full");
    return "safe diagnostic";
  });
  const outer = vi.fn();
  render(<SupportPanel onClose={vi.fn()} onError={outer} />);
  await screen.findByText("safe diagnostic");
  fireEvent.click(
    screen.getByRole("button", { name: "Save diagnostic report" }),
  );
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    "Disk full",
  );
  expect(outer).not.toHaveBeenCalled();
  expect(
    (
      screen.getByRole("button", {
        name: "Save diagnostic report",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(false);
});

it("cannot save a previous instruction document after the next document fails to load", async () => {
  vi.mocked(call)
    .mockResolvedValueOnce({ content: "Document A" })
    .mockRejectedValueOnce(new Error("Read B failed"));
  const error = vi.fn();
  const { rerender } = render(
    <TaskInstructions id="a" title="Instructions" onError={error} />,
  );
  await screen.findByDisplayValue("Document A");
  rerender(<TaskInstructions id="b" title="Instructions" onError={error} />);
  await screen.findByText("The instruction document could not be loaded.");
  expect(screen.queryByDisplayValue("Document A")).toBeNull();
  expect(
    (
      screen.getByRole("button", {
        name: "Save instructions",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  vi.mocked(call).mockResolvedValue({ content: "Document B" });
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  fireEvent.change(await screen.findByDisplayValue("Document B"), {
    target: { value: "Edited B" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save instructions" }));
  await waitFor(() =>
    expect(call).toHaveBeenCalledWith("instructions.save", {
      id: "b",
      content: "Edited B",
    }),
  );
});

it("ignores late instruction reads after switching documents", async () => {
  let finish!: (value: object) => void;
  vi.mocked(call).mockImplementation(async (_command, payload) =>
    payload?.id === "a"
      ? new Promise((resolve) => {
          finish = resolve;
        })
      : { content: "Current B" },
  );
  const { rerender } = render(
    <TaskInstructions id="a" title="Instructions" onError={vi.fn()} />,
  );
  rerender(<TaskInstructions id="b" title="Instructions" onError={vi.fn()} />);
  await screen.findByDisplayValue("Current B");
  await act(async () => finish({ content: "Late A" }));
  expect(screen.getByDisplayValue("Current B")).toBeTruthy();
  expect(screen.queryByDisplayValue("Late A")).toBeNull();
});

it("handles cancellation failures without an unhandled rejection or duplicated request", async () => {
  let fail!: (reason: Error) => void;
  vi.mocked(call).mockImplementation(
    () =>
      new Promise((_resolve, reject) => {
        fail = reject;
      }),
  );
  const report = vi.fn();
  render(
    <ActivityPage
      jobs={[{ id: "job", type: "chat.send", state: "running" }]}
      refresh={async () => {}}
      onReport={report}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Stop" }));
  expect(
    (screen.getByRole("button", { name: "Stopping…" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  expect(call).toHaveBeenCalledOnce();
  await act(async () => fail(new Error("Engine disconnected")));
  expect(screen.getByRole("alert").textContent).toContain(
    "Engine disconnected",
  );
  fireEvent.click(screen.getByRole("button", { name: "Report problem" }));
  expect(report).toHaveBeenCalledWith("JOB_CANCEL_FAILED");
  expect(screen.getByRole("button", { name: "Stop" })).toBeTruthy();
});

it("preserves the actual failure code when reporting a background task", () => {
  const report = vi.fn();
  render(
    <ActivityPage
      jobs={[
        {
          id: "job",
          type: "chat.send",
          state: "failed",
          error_code: "MODEL_UNSUPPORTED",
        },
      ]}
      refresh={async () => {}}
      onReport={report}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Report problem" }));
  expect(report).toHaveBeenCalledWith("MODEL_UNSUPPORTED");
});

it("does not label an unsuccessful update check as up to date", async () => {
  vi.mocked(invoke).mockRejectedValue(new Error("Offline"));
  const error = vi.fn();
  render(<Updates onError={error} />);
  fireEvent.click(screen.getByRole("button", { name: "Check for updates" }));
  await waitFor(() => expect(error).toHaveBeenCalledWith("Error: Offline"));
  expect(screen.queryByText("No newer version is available.")).toBeNull();
});

it("distinguishes installing from checking and recovers from install failure", async () => {
  let progress!: (event: { payload: object }) => void,
    fail!: (reason: Error) => void;
  vi.mocked(listen).mockImplementation(async (_event, handler) => {
    progress = handler as typeof progress;
    return vi.fn<() => void>();
  });
  vi.mocked(invoke).mockImplementation(async (command) =>
    command === "check_update"
      ? { update: { version: "9.0", notes: "Fixes" } }
      : new Promise((_resolve, reject) => {
          fail = reject;
        }),
  );
  const error = vi.fn();
  render(<Updates onError={error} />);
  fireEvent.click(screen.getByRole("button", { name: "Check for updates" }));
  fireEvent.click(
    await screen.findByRole("button", { name: "Install and restart" }),
  );
  expect(
    screen.getByRole("button", { name: "Installing update…" }),
  ).toBeTruthy();
  expect(screen.queryByRole("button", { name: "Checking…" })).toBeNull();
  act(() => progress({ payload: { downloaded: 2e6, total: 4e6 } }));
  expect(screen.getByRole("progressbar").getAttribute("value")).toBe("2000000");
  await act(async () => fail(Error("Disk full")));
  expect(error).toHaveBeenCalledWith("Error: Disk full");
  expect(
    (
      screen.getByRole("button", {
        name: "Install and restart",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(false);
});

it("offers timezone choices and never submits an empty report time", async () => {
  sessionStorage.setItem("settings-tab", "daily");
  vi.mocked(call).mockImplementation(async (command) =>
    command === "instructions.get"
      ? { content: "Daily instructions" }
      : {
          settings: {
            enabled: false,
            hour: 22,
            minute: 0,
            timezone: "Asia/Riyadh",
            language: "ar",
          },
          reports: [],
        },
  );
  render(
    <Settings
      snapshot={{}}
      refresh={async () => {}}
      theme="light"
      setTheme={vi.fn()}
      onError={vi.fn()}
    />,
  );
  const time = await screen.findByLabelText("Report time");
  const zones = screen.getByRole("combobox", {
    name: "Time zone",
  }) as HTMLSelectElement;
  expect(zones.value).toBe("Asia/Riyadh");
  fireEvent.change(time, { target: { value: "" } });
  expect(
    (screen.getByRole("button", { name: "Save schedule" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  fireEvent.change(time, { target: { value: "18:45" } });
  fireEvent.change(zones, { target: { value: "UTC" } });
  fireEvent.click(screen.getByRole("button", { name: "Save schedule" }));
  await waitFor(() =>
    expect(call).toHaveBeenCalledWith("daily.set", {
      enabled: false,
      hour: 18,
      minute: 45,
      timezone: "UTC",
      language: "ar",
      consent: true,
    }),
  );
});

it("requires an explicit decision before replacing a workspace", async () => {
  sessionStorage.setItem("settings-tab", "privacy");
  render(
    <Settings
      snapshot={{}}
      refresh={async () => {}}
      theme="light"
      setTheme={vi.fn()}
      onError={vi.fn()}
    />,
  );
  const summary = await screen.findByText(
    "Advanced: import a legacy workspace",
  );
  summary.closest("details")!.open = true;
  fireEvent.click(
    screen.getByRole("button", { name: "Import original workspace" }),
  );
  await screen.findByRole("dialog", { name: "Import legacy workspace?" });
  expect(invoke).not.toHaveBeenCalledWith(
    "transfer_workspace",
    expect.anything(),
  );
  fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(invoke).not.toHaveBeenCalledWith(
    "transfer_workspace",
    expect.anything(),
  );
});

it("keeps an acknowledged stop separate from a failed list refresh", async () => {
  vi.mocked(call).mockResolvedValue({ cancelled: true });
  render(
    <ActivityPage
      jobs={[{ id: "j", state: "running", type: "chat.send" }]}
      refresh={async () => {
        throw new Error("Refresh unavailable");
      }}
      onReport={vi.fn()}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Stop" }));
  await screen.findByText(
    "Stop requested. The task list will refresh automatically.",
  );
  expect(
    (
      screen.getByRole("button", {
        name: "Stop requested",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  expect(screen.queryByRole("alert")).toBeNull();
  expect(screen.queryByRole("button", { name: "Report problem" })).toBeNull();
});

it("shows report export progress on the save action and locks its reviewed content", async () => {
  let finish: (path: string) => void = () => {};
  vi.mocked(invoke).mockImplementation(async (command) =>
    command === "export_diagnostics"
      ? new Promise((resolve) => {
          finish = resolve;
        })
      : "safe diagnostic",
  );
  render(
    <SupportPanel
      article={{
        title: "A story",
        url: "https://example.com",
        source: "News",
        articleId: "a",
        stage: "ready",
        elapsedMs: 2,
        bodyStatus: "full",
      }}
      onClose={vi.fn()}
      onError={vi.fn()}
    />,
  );
  await screen.findByText(/safe diagnostic/);
  fireEvent.click(
    screen.getByRole("button", { name: "Save diagnostic report" }),
  );
  expect(
    screen
      .getByRole("button", { name: "Saving report…" })
      .querySelector(".spin"),
  ).toBeTruthy();
  expect(
    screen
      .getByRole("button", { name: "Report a problem on GitHub" })
      .querySelector(".spin"),
  ).toBeNull();
  expect((screen.getByRole("checkbox") as HTMLInputElement).disabled).toBe(
    true,
  );
  expect(
    (screen.getByRole("button", { name: "Close" }) as HTMLButtonElement)
      .disabled,
  ).toBe(true);
  await act(async () => finish("/tmp/safe-report.txt"));
  await screen.findByText("/tmp/safe-report.txt");
  expect((screen.getByRole("checkbox") as HTMLInputElement).disabled).toBe(
    false,
  );
});

it("removes a stale up-to-date result when a subsequent update check fails", async () => {
  vi.mocked(invoke)
    .mockResolvedValueOnce({ update: null })
    .mockRejectedValueOnce(new Error("Offline"));
  render(<Updates onError={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Check for updates" }));
  await screen.findByText("No newer version is available.");
  fireEvent.click(screen.getByRole("button", { name: "Check for updates" }));
  await waitFor(() => expect(vi.mocked(invoke).mock.calls).toHaveLength(2));
  expect(screen.queryByText("No newer version is available.")).toBeNull();
});

it("refreshes saved reports without replacing schedule edits", async () => {
  sessionStorage.setItem("settings-tab", "daily");
  let poll: () => Promise<void> = async () => {};
  const original = globalThis.setInterval;
  vi.spyOn(globalThis, "setInterval").mockImplementation(((
    callback: () => Promise<void>,
    milliseconds: number,
  ) => {
    if (milliseconds !== 15000) return original(callback, milliseconds);
    poll = callback;
    return 1;
  }) as typeof setInterval);
  Object.defineProperty(document, "visibilityState", {
    configurable: true,
    value: "visible",
  });
  let reads = 0;
  vi.mocked(call).mockImplementation(async (command) =>
    command === "daily.get"
      ? {
          settings: {
            enabled: false,
            hour: 22,
            minute: 0,
            timezone: "UTC",
            language: "en",
          },
          reports:
            ++reads > 1
              ? [
                  {
                    day: "2026-10-24",
                    state: "ready",
                    body: "A freshly prepared report",
                  },
                ]
              : [],
        }
      : { content: "Daily instructions" },
  );
  render(
    <Settings
      snapshot={{}}
      refresh={async () => {}}
      theme="light"
      setTheme={vi.fn()}
      onError={vi.fn()}
    />,
  );
  const time = await screen.findByLabelText("Report time");
  fireEvent.change(time, { target: { value: "09:15" } });
  await act(async () => poll());
  expect((time as HTMLInputElement).value).toBe("09:15");
  expect(await screen.findByText("2026-10-24")).toBeTruthy();
  fireEvent.click(screen.getByText("2026-10-24"));
  expect(screen.getByText("A freshly prepared report")).toBeTruthy();
});
