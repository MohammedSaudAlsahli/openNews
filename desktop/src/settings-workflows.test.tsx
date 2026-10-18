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
import { call } from "./engine";
import { TaskInstructions } from "./task-instructions";
import { Connections } from "./connections";
vi.mock("./engine", () => ({ call: vi.fn(), language: () => "en" }));
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
it("loads the actual task instructions and saves edits to the same document", async () => {
  vi.mocked(call).mockResolvedValue({ content: "# Explain the whole article" });
  render(
    <TaskInstructions
      id="article-summary"
      title="Article instructions"
      onError={vi.fn()}
    />,
  );
  const editor = await screen.findByDisplayValue("# Explain the whole article");
  fireEvent.change(editor, { target: { value: "# Explain with context" } });
  fireEvent.click(screen.getByText("Save instructions"));
  await waitFor(() =>
    expect(call).toHaveBeenCalledWith("instructions.save", {
      id: "article-summary",
      content: "# Explain with context",
    }),
  );
  expect(await screen.findByText("Saved")).toBeTruthy();
});
it("shows actual provider catalog failures instead of silently empty model choices", async () => {
  const error = vi.fn();
  vi.mocked(call).mockImplementation(async (command: string) =>
    command === "providers.catalog"
      ? { providers: [] }
      : { models: [], error: "Connection expired" },
  );
  render(
    <Connections
      snapshot={{
        profiles: [{ id: "test", provider_key: "openai", model_id: "" }],
      }}
      refresh={async () => {}}
      onError={error}
    />,
  );
  fireEvent.click(screen.getByText("Manage account"));
  fireEvent.click(screen.getByText("Refresh models"));
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    "Connection expiredDismiss",
  );
  expect(error).not.toHaveBeenCalled();
});

it("keeps adding an account separate and advanced server settings collapsed", async () => {
  vi.mocked(call).mockResolvedValue({
    providers: [
      {
        id: "ollama",
        name: "Ollama",
        status: "ready",
        credential: "local_server",
        fields: ["host"],
      },
    ],
  });
  render(
    <Connections
      snapshot={{
        profiles: [{ id: "p", label: "My account", model_id: "model" }],
      }}
      refresh={async () => {}}
      onError={vi.fn()}
    />,
  );
  expect(screen.queryByLabelText("Provider")).toBeNull();
  fireEvent.click(screen.getByText("Add account"));
  await screen.findByText("Ollama");
  expect(
    screen.getByText("Advanced connection options").closest("details")?.open,
  ).toBe(false);
  fireEvent.click(screen.getByText("Cancel"));
  expect(screen.queryByLabelText("Provider")).toBeNull();
});

it("shows saved health and live check failures without leaving a green ready state", async () => {
  let rejectCheck: (reason: Error) => void = () => {};
  vi.mocked(call).mockImplementation(async (command) => {
    if (command === "providers.check")
      return new Promise((_resolve, reject) => {
        rejectCheck = reject;
      });
    return { providers: [] };
  });
  render(
    <Connections
      snapshot={{ profiles: [{ id: "p", connection: { state: "connected" } }] }}
      refresh={async () => {}}
      onError={vi.fn()}
    />,
  );
  expect(screen.getByText(/Ready/)).toBeTruthy();
  fireEvent.click(screen.getByText("Check connection"));
  expect(screen.queryByText(/^Ready$/)).toBeNull();
  expect(screen.getAllByText(/Checking connection/).length).toBeGreaterThan(0);
  rejectCheck(new Error("Network offline"));
  expect(await screen.findByText("Network offline")).toBeTruthy();
  expect(screen.getByText(/Could not verify/)).toBeTruthy();
});

it("does not call a saved but unchecked account ready", async () => {
  vi.mocked(call).mockResolvedValue({ providers: [] });
  render(
    <Connections
      snapshot={{
        profiles: [{ id: "p", connection: { state: "configured" } }],
      }}
      refresh={async () => {}}
      onError={vi.fn()}
    />,
  );
  expect(screen.getByText(/Not checked yet/)).toBeTruthy();
  expect(screen.getByText("Check connection")).toBeTruthy();
});

it("groups customization without losing instruction edits when opening references", async () => {
  const { default: Settings } = await import("./settings");
  sessionStorage.setItem("settings-tab", "instructions");
  vi.mocked(call).mockResolvedValue({
    settings: { role: "Original instructions" },
  });
  render(
    <Settings
      snapshot={{ sources: [] }}
      refresh={async () => {}}
      theme="dark"
      setTheme={vi.fn()}
      onError={vi.fn()}
    />,
  );
  const editor = await screen.findByDisplayValue("Original instructions");
  fireEvent.change(editor, { target: { value: "My edited instructions" } });
  fireEvent.click(screen.getByText("Examples & references"));
  fireEvent.click(screen.getByText("Instructions & style"));
  expect(screen.getByDisplayValue("My edited instructions")).toBeTruthy();
  expect(
    screen.queryByRole("button", { name: /^Assistants$/ }),
  ).toBeNull();
  expect(
    screen.getByText("Advanced: specialized assistants").closest("details")
      ?.open,
  ).toBe(false);
  fireEvent.click(screen.getByText("Save instructions"));
  await waitFor(() =>
    expect(call).toHaveBeenCalledWith("assistant.save", {
      scope: "general",
      target_id: "",
      settings: { role: "My edited instructions" },
    }),
  );
  sessionStorage.clear();
});
