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
import { ConversationOptions } from "./conversation-options";
import { call } from "./engine";
import { getLocale, setLocale, t, useLocale } from "./locale";
vi.mock("./engine", () => ({ call: vi.fn(), language: () => "en" }));
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
afterEach(() => {
  cleanup();
  setLocale("en");
  vi.resetAllMocks();
});
it("attaches the saved article ID, not arbitrary page text", async () => {
  vi.mocked(call).mockResolvedValue({
    articles: [{ id: "article-1", title: "A complete story" }],
  });
  const selected = vi.fn();
  render(
    <ConversationOptions
      conversation=""
      selected={[]}
      onSelect={selected}
      onError={vi.fn()}
    />,
  );
  fireEvent.click(await screen.findByLabelText("A complete story"));
  expect(selected).toHaveBeenCalledWith([
    { id: "article-1", title: "A complete story" },
  ]);
});
it("preserves other conversation preferences when editing working instructions", async () => {
  vi.mocked(call).mockImplementation(async (command) =>
    command === "assistant.get"
      ? {
          settings: {
            instructions: "Existing guidance",
            style: "Keep my style",
          },
        }
      : { articles: [] },
  );
  render(
    <ConversationOptions
      conversation="chat-1"
      selected={[]}
      onSelect={vi.fn()}
      onError={vi.fn()}
    />,
  );
  fireEvent.click(screen.getByText("Conversation instructions"));
  const editor = await screen.findByDisplayValue("Existing guidance");
  fireEvent.change(editor, { target: { value: "Explain the evidence" } });
  fireEvent.click(screen.getByText("Save instructions"));
  await waitFor(() =>
    expect(call).toHaveBeenCalledWith("assistant.save", {
      scope: "conversation",
      target_id: "chat-1",
      settings: {
        instructions: "Explain the evidence",
        style: "Keep my style",
      },
    }),
  );
});
it("switches interface language live without changing model content", () => {
  function Example() {
    useLocale();
    return (
      <>
        <h1>{t("Articles")}</h1>
        <button onClick={() => setLocale(getLocale() === "en" ? "ar" : "en")}>
          Switch
        </button>
      </>
    );
  }
  render(<Example />);
  fireEvent.click(screen.getByText("Switch"));
  expect(screen.getByRole("heading").textContent).toBe("المقالات");
  expect(document.documentElement.dir).toBe("rtl");
  fireEvent.click(screen.getByText("Switch"));
  expect(screen.getByRole("heading").textContent).toBe("Articles");
  expect(document.documentElement.dir).toBe("ltr");
});
