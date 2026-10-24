// @vitest-environment jsdom
import React from "react";
import { afterEach, expect, it, vi } from "vitest";
import {
  cleanup,
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { ConversationOptions } from "./conversation-options";
import { call } from "./engine";
import { getLocale, setLocale, t, useLocale } from "./locale";
import { navigateSafely } from "./unsaved-changes";
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

it("locks instructions until loaded, offers retry, and protects unsaved edits on close and navigation", async () => {
  let attempts = 0;
  vi.mocked(call).mockImplementation(async (command) => {
    if (command === "assistant.get") {
      if (++attempts === 1) throw new Error("Connection interrupted");
      return { settings: { instructions: "Saved guidance" } };
    }
    return { articles: [] };
  });
  const close = vi.fn(),
    leave = vi.fn();
  render(
    <ConversationOptions
      conversation="chat-1"
      selected={[]}
      onSelect={vi.fn()}
      onError={vi.fn()}
      onClose={close}
    />,
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Conversation instructions" }),
  );
  expect(
    (
      screen.getByRole("textbox", {
        name: "Conversation instructions",
      }) as HTMLTextAreaElement
    ).disabled,
  ).toBe(true);
  await screen.findByText("Connection interrupted");
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  const editor = await screen.findByDisplayValue("Saved guidance");
  fireEvent.change(editor, { target: { value: "Keep these edits" } });
  fireEvent.click(screen.getByRole("button", { name: "Close" }));
  expect(close).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Keep editing" }));
  act(() => navigateSafely(leave));
  expect(leave).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Save and continue" }));
  await waitFor(() => expect(leave).toHaveBeenCalledTimes(1));
  expect(call).toHaveBeenCalledWith(
    "assistant.save",
    expect.objectContaining({ settings: { instructions: "Keep these edits" } }),
  );
});

it("attaches an imported URL to the current selection instead of restoring removed articles", async () => {
  let finish: (value: unknown) => void = () => {};
  vi.mocked(call).mockImplementation(async (command) =>
    command === "news.import"
      ? new Promise((resolve) => {
          finish = resolve;
        })
      : { articles: [] },
  );
  const select = vi.fn();
  const { rerender } = render(
    <ConversationOptions
      conversation=""
      selected={[{ id: "removed", title: "Removed article" }]}
      onSelect={select}
      onError={vi.fn()}
    />,
  );
  fireEvent.change(
    screen.getByRole("textbox", { name: "Attach an article link" }),
    { target: { value: "https://example.com/story" } },
  );
  fireEvent.click(screen.getByRole("button", { name: "Attach article" }));
  rerender(
    <ConversationOptions
      conversation=""
      selected={[{ id: "new", title: "Another article" }]}
      onSelect={select}
      onError={vi.fn()}
    />,
  );
  await act(async () =>
    finish({ article_id: "imported", title: "Imported story" }),
  );
  expect(select).toHaveBeenCalledWith([
    { id: "new", title: "Another article" },
    { id: "imported", title: "Imported story" },
  ]);
});
