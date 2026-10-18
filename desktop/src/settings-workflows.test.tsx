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
