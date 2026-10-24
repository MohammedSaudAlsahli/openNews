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
  within,
} from "@testing-library/react";
import { Articles } from "./pages";
import { call } from "./engine";
vi.mock("./engine", async (original) => ({
  ...(await original<typeof import("./engine")>()),
  call: vi.fn(),
}));
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn().mockResolvedValue(null),
}));
beforeEach(() => {
  vi.stubGlobal("localStorage", { getItem: () => null, setItem: vi.fn() });
});
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});
const articles = [
  {
    id: "one",
    title: "First article",
    body_status: "full",
    text: "First cached body",
    prepared_summary: { summary: "First explanation" },
  },
  {
    id: "two",
    title: "Second article",
    body_status: "full",
    text: "Second cached body",
    prepared_summary: { summary: "Second explanation" },
  },
];
function base(command: string, payload: any) {
  if (command === "news.list") return { articles, has_more: false };
  if (command === "news.article")
    return articles.find((a) => a.id === payload.article_id);
  if (command === "news.related") return { articles: [] };
  if (command === "news.summary.states") return { states: {} };
  return {};
}
it("opens explanation settings instead of enabling a missing model from the article list", async () => {
  vi.spyOn(document, "visibilityState", "get").mockReturnValue("hidden");
  vi.mocked(call).mockImplementation(async (command, payload) =>
    command === "news.digest.status"
      ? { enabled: false }
      : base(command, payload),
  );
  const configure = vi.fn();
  render(
    <Articles
      snapshot={{}}
      onError={vi.fn()}
      onConfigureExplanations={configure}
    />,
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Explanation settings" }),
  );
  expect(configure).toHaveBeenCalledOnce();
  expect(
    vi
      .mocked(call)
      .mock.calls.some(([command]) => command === "news.digest.set"),
  ).toBe(false);
});
it("keeps exactly one explanation and history section across reader updates", async () => {
  const errors = vi.spyOn(console, "error").mockImplementation(() => {});
  vi.mocked(call).mockImplementation(async (command, payload) =>
    base(command, payload),
  );
  const { container, rerender } = render(
    <Articles snapshot={{}} onError={vi.fn()} />,
  );
  fireEvent.click(await screen.findByRole("button", { name: "First article" }));
  await screen.findByText("First cached body");
  for (let i = 0; i < 3; i++) {
    fireEvent.click(screen.getByRole("button", { name: "Bookmark" }));
    await waitFor(() =>
      expect(
        screen
          .getByRole("button", { name: "Bookmark" })
          .hasAttribute("disabled"),
      ).toBe(false),
    );
    rerender(<Articles snapshot={{ tick: i }} onError={vi.fn()} />);
  }
  expect(container.querySelectorAll(".article-explanation")).toHaveLength(1);
  expect(container.querySelectorAll(".article-history")).toHaveLength(1);
  expect(
    errors.mock.calls.filter((args) => args.join(" ").includes("same key")),
  ).toHaveLength(0);
});
it("does not reopen the previous article when a late bookmark response finishes", async () => {
  let finish: (result: unknown) => void = () => {};
  vi.mocked(call).mockImplementation(async (command, payload) =>
    command === "news.bookmark"
      ? new Promise((resolve) => {
          finish = resolve;
        })
      : base(command, payload),
  );
  const { container } = render(<Articles snapshot={{}} onError={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", { name: "First article" }));
  await screen.findByText("First cached body");
  fireEvent.click(screen.getByRole("button", { name: "Bookmark" }));
  fireEvent.click(
    within(container.querySelector(".reader-toolbar") as HTMLElement).getByRole(
      "button",
      { name: "Articles" },
    ),
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Second article" }),
  );
  await screen.findByText("Second cached body");
  await act(async () => finish({ saved: true }));
  expect(screen.getByRole("heading", { name: "Second article" })).toBeTruthy();
  expect(screen.queryByText("First cached body")).toBeNull();
  expect(
    screen
      .getByRole("button", { name: "Bookmark" })
      .getAttribute("aria-pressed"),
  ).toBe("false");
});
