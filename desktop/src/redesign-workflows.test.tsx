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
import { SourcesPage } from "./sources-page";
import { DraftsPage } from "./drafts-page";
import { ChatComposer } from "./chat-composer";
import { navigateSafely } from "./unsaved-changes";
vi.mock("./engine", async (original) => ({
  ...(await original<typeof import("./engine")>()),
  call: vi.fn(),
}));
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  vi.useRealTimers();
});

it("pages large source directories and resets the page when language changes", async () => {
  const feeds = Array.from({ length: 80 }, (_, i) => ({
    id: String(i),
    title: `Source ${i}`,
    url: `https://source${i}.example/feed`,
    language: i < 40 ? "en" : "ar",
    category: i % 2 ? "science" : "business",
  }));
  vi.mocked(call).mockResolvedValue({ feeds });
  render(
    <SourcesPage snapshot={{}} refresh={async () => {}} onError={vi.fn()} />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Discover" }));
  await screen.findByRole("heading", { name: "Source 0" });
  expect(
    screen.queryByRole("heading", { name: "Source 36" }),
  ).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Show more sources" }));
  expect(
    screen.getByRole("heading", { name: "Source 71" }),
  ).toBeTruthy();
  expect(
    screen.queryByRole("heading", { name: "Source 72" }),
  ).toBeNull();
  fireEvent.change(screen.getByRole("combobox", { name: "Source language" }), {
    target: { value: "ar" },
  });
  expect(
    screen.queryByRole("heading", { name: "Source 0" }),
  ).toBeNull();
  expect(
    screen.getByRole("heading", { name: "Source 40" }),
  ).toBeTruthy();
  expect(
    screen.queryByRole("heading", { name: "Source 76" }),
  ).toBeNull();
});

it("clears source filters without taking a following search to discovery", async () => {
  vi.mocked(call).mockResolvedValue({ feeds: [] });
  render(
    <SourcesPage
      snapshot={{
        subscriptions: [
          { id: "saved", title: "My publisher", url: "https://example.com" },
        ],
      }}
      refresh={async () => {}}
      onError={vi.fn()}
    />,
  );
  fireEvent.change(
    screen.getByRole("textbox", { name: "Search sources or topics" }),
    { target: { value: "missing" } },
  );
  expect(
    screen.getByRole("heading", { name: "No sources match your search" }),
  ).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
  expect(screen.getByRole("heading", { name: "My publisher" })).toBeTruthy();
  expect(
    screen
      .getByRole("button", { name: /Following/ })
      .getAttribute("aria-pressed"),
  ).toBe("true");
});

it("shows curated discovery immediately and marks existing subscriptions as followed", async () => {
  vi.mocked(call).mockResolvedValue({
    feeds: [
      {
        id: "one",
        title: "Epoch AI",
        url: "https://epoch.ai/feed",
        description_en: "Research and analysis",
      },
    ],
  });
  render(
    <SourcesPage
      snapshot={{
        subscriptions: [
          { id: "saved", title: "Epoch AI", url: "https://epoch.ai/feed" },
        ],
      }}
      refresh={async () => {}}
      onError={vi.fn()}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Discover" }));
  await screen.findByRole("heading", { name: "Epoch AI" });
  expect(
    screen.getByRole("button", { name: "Following" }).hasAttribute("disabled"),
  ).toBe(true);
  expect(
    vi
      .mocked(call)
      .mock.calls.some(([command]) => command === "news.directory"),
  ).toBe(false);
});

it("ignores a late directory response after the user changes the query", async () => {
  let resolveOld: (value: unknown) => void = () => {};
  vi.mocked(call).mockImplementation(async (command, p) => {
    if (command === "news.curated") return { feeds: [] };
    if (command === "news.directory" && p?.query === "old")
      return new Promise((resolve) => {
        resolveOld = resolve;
      });
    return {
      feeds: [
        {
          id: "new",
          title: "New query result",
          url: "https://new.example/feed",
        },
      ],
    };
  });
  render(
    <SourcesPage snapshot={{}} refresh={async () => {}} onError={vi.fn()} />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Discover" }));
  fireEvent.change(
    screen.getByRole("textbox", { name: "Search sources or topics" }),
    { target: { value: "old" } },
  );
  await waitFor(() =>
    expect(call).toHaveBeenCalledWith("news.directory", {
      query: "old",
      cursor: undefined,
    }),
  );
  fireEvent.change(
    screen.getByRole("textbox", { name: "Search sources or topics" }),
    { target: { value: "new" } },
  );
  await screen.findByRole("heading", { name: "New query result" });
  await act(async () =>
    resolveOld({
      feeds: [
        { id: "old", title: "Old result", url: "https://old.example/feed" },
      ],
    }),
  );
  expect(
    screen.getByRole("heading", { name: "New query result" }),
  ).toBeTruthy();
  expect(screen.queryByRole("heading", { name: "Old result" })).toBeNull();
});

it("starts a blank draft and prevents page navigation until changes are resolved", async () => {
  render(<DraftsPage snapshot={{ drafts: [] }} onError={vi.fn()} />);
  fireEvent.click(screen.getAllByRole("button", { name: "New draft" })[0]);
  const editor = screen.getByRole("textbox", {
    name: "Draft text",
  }) as HTMLTextAreaElement;
  expect(editor.value).toBe("");
  fireEvent.change(editor, { target: { value: "A draft I am still writing" } });
  const leave = vi.fn();
  act(() => navigateSafely(leave));
  expect(leave).not.toHaveBeenCalled();
  fireEvent.click(await screen.findByRole("button", { name: "Keep editing" }));
  expect(editor.value).toBe("A draft I am still writing");
  act(() => navigateSafely(leave));
  fireEvent.click(
    await screen.findByRole("button", { name: "Discard changes" }),
  );
  expect(leave).toHaveBeenCalledOnce();
});

it("keeps unsaved text and the navigation decision when saving fails", async () => {
  vi.mocked(call).mockRejectedValue(new Error("Disk full"));
  const error = vi.fn(),
    leave = vi.fn();
  render(<DraftsPage snapshot={{ drafts: [] }} onError={error} />);
  fireEvent.click(screen.getAllByRole("button", { name: "New draft" })[0]);
  fireEvent.change(screen.getByRole("textbox", { name: "Title" }), {
    target: { value: "My draft" },
  });
  fireEvent.change(screen.getByRole("textbox", { name: "Draft text" }), {
    target: { value: "Do not lose this" },
  });
  act(() => navigateSafely(leave));
  fireEvent.click(
    await screen.findByRole("button", { name: "Save and continue" }),
  );
  await waitFor(() => expect(error).toHaveBeenCalledWith("Error: Disk full"));
  expect(leave).not.toHaveBeenCalled();
  expect(screen.getByRole("dialog")).toBeTruthy();
});

it("sends on Enter, preserves Shift+Enter, and offers a stop action while running", () => {
  const send = vi.fn(),
    stop = vi.fn();
  const props = {
    message: "Explain this story",
    onMessage: vi.fn(),
    onSend: send,
    onStop: stop,
    running: false,
    sending: false,
    ready: true,
    onArticles: vi.fn(),
    onFile: vi.fn(),
    onArticle: vi.fn(),
    onError: vi.fn(),
    includeNews: true,
    researchWeb: false,
    onNews: vi.fn(),
    onWeb: vi.fn(),
    agents: [],
    agent: "",
    onAgent: vi.fn(),
    attachments: null,
  };
  const { rerender } = render(<ChatComposer {...props} />);
  fireEvent.keyDown(screen.getByRole("textbox", { name: "Message" }), {
    key: "Enter",
    shiftKey: true,
  });
  expect(send).not.toHaveBeenCalled();
  fireEvent.keyDown(screen.getByRole("textbox", { name: "Message" }), {
    key: "Enter",
  });
  expect(send).toHaveBeenCalledOnce();
  rerender(<ChatComposer {...props} running />);
  fireEvent.click(screen.getByRole("button", { name: "Stop response" }));
  expect(stop).toHaveBeenCalledOnce();
});
