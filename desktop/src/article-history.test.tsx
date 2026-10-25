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
import { ArticleHistory, articleChanges } from "./article-history";
import { call } from "./engine";
vi.mock("./engine", async (original) => ({
  ...(await original<typeof import("./engine")>()),
  call: vi.fn(),
}));
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
const date = "2026-10-24T00:00:00Z";
function expand() {
  const details = screen.getByText("Article history").closest("details")!;
  details.open = true;
  fireEvent(details, new Event("toggle"));
}
const diff =
  "--- title (before)\n+++ title (after)\n@@ -1 +1 @@\n-Old headline\n+Updated headline\n--- text (before)\n+++ text (after)\n@@ -3,2 +3,2 @@\n A retained paragraph\n-Old detail\n+New detail";

it("keeps fields, context and old/new line numbers when parsing article changes", () => {
  const groups = articleChanges(diff);
  expect(groups.map((group) => group.field)).toEqual(["title", "text"]);
  expect(groups[1].lines).toEqual([
    { kind: "context", text: "A retained paragraph", before: 3, after: 3 },
    { kind: "removed", text: "Old detail", before: 4 },
    { kind: "added", text: "New detail", after: 4 },
  ]);
});
it("opens the latest comparison grouped by field, without treating the baseline as additions", async () => {
  vi.mocked(call).mockImplementation(async (command, payload) =>
    command === "news.history"
      ? {
          revisions: [
            { id: 2, captured_at: date },
            { id: 1, captured_at: date },
          ],
        }
      : payload?.revision_id === 2
        ? { id: 2, previous_id: 1, diff }
        : {
            id: 1,
            previous_id: null,
            content: {
              title: "Original headline",
              text: "Original article body",
            },
            diff: "--- text (before)\n+++ text (after)\n@@ -0,0 +1 @@\n+Original article body",
          },
  );
  render(<ArticleHistory articleId="news" />);
  expand();
  await screen.findByRole("heading", { name: "Article text" });
  expect(screen.getByText("New detail")).toBeTruthy();
  expect(screen.getByText(/2 added lines/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: /First saved version/ }));
  await screen.findByText("Original article body");
  expect(screen.queryByText("added lines")).toBeNull();
  expect(screen.queryByText("New detail")).toBeNull();
});
it("ignores an older comparison response after another version is selected", async () => {
  let finishOld: (value: unknown) => void = () => {};
  vi.mocked(call).mockImplementation(async (command, payload) => {
    if (command === "news.history")
      return {
        revisions: [
          { id: 3, captured_at: date },
          { id: 2, captured_at: date },
          { id: 1, captured_at: date },
        ],
      };
    if (payload?.revision_id === 3)
      return new Promise((resolve) => {
        finishOld = resolve;
      });
    return { id: 2, previous_id: 1, diff };
  });
  render(<ArticleHistory articleId="news" />);
  expand();
  fireEvent.click(
    await screen.findByRole("button", { name: /Earlier saved version/ }),
  );
  await screen.findByText("New detail");
  await act(async () =>
    finishOld({
      id: 3,
      previous_id: 2,
      diff: diff.replace("New detail", "Stale detail"),
    }),
  );
  expect(screen.queryByText("Stale detail")).toBeNull();
  expect(screen.getByText("New detail")).toBeTruthy();
});
it("keeps history errors local and retries an empty history without a persistent spinner", async () => {
  vi.mocked(call)
    .mockRejectedValueOnce(new Error("Archive unavailable"))
    .mockResolvedValue({ revisions: [] });
  render(<ArticleHistory articleId="news" />);
  expand();
  await screen.findByText("Archive unavailable");
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));
  await screen.findByText(
    "No saved versions yet. Versions appear when article content changes.",
  );
  expect(screen.queryByRole("alert")).toBeNull();
  expect(screen.queryByText("Loading changes…")).toBeNull();
});
it("limits large comparisons initially and reveals the remaining original lines on demand", async () => {
  const large =
    "--- text (before)\n+++ text (after)\n@@ -0,0 +1,450 @@\n" +
    Array.from({ length: 450 }, (_, i) => `+Added paragraph ${i}`).join("\n");
  vi.mocked(call).mockImplementation(async (command) =>
    command === "news.history"
      ? { revisions: [{ id: 2, captured_at: date }] }
      : { id: 2, previous_id: 1, diff: large },
  );
  render(<ArticleHistory articleId="news" />);
  expand();
  await screen.findByText("Added paragraph 399");
  expect(screen.queryByText("Added paragraph 449")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Show more changes" }));
  await waitFor(() =>
    expect(screen.getByText("Added paragraph 449")).toBeTruthy(),
  );
});

it("folds retained context, shows a hunk gap once and opens the stored article without another request", async () => {
  const separated =
    "--- text (before)\n+++ text (after)\n@@ -1,4 +1,4 @@\n Context one\n Context two\n Context three\n-Old detail\n+New detail\n@@ -20 +20 @@\n-Later old\n+Later new";
  vi.mocked(call).mockImplementation(async (command) =>
    command === "news.history"
      ? {
          revisions: [
            { id: 2, captured_at: date },
            { id: 1, captured_at: date },
          ],
        }
      : {
          id: 2,
          previous_id: 1,
          diff: separated,
          content: { text: "Complete saved article including unchanged text" },
        },
  );
  render(<ArticleHistory articleId="news" />);
  expand();
  const toggle = await screen.findByRole("button", {
    name: "Show 3 unchanged lines",
  });
  expect(screen.queryByText("Context one")).toBeNull();
  fireEvent.click(toggle);
  expect(screen.getByText("Context one")).toBeTruthy();
  expect(screen.getByText("Context three")).toBeTruthy();
  expect(
    screen.getAllByRole("button", { name: "Hide 3 unchanged lines" }),
  ).toHaveLength(1);
  fireEvent.click(
    screen.getByRole("button", { name: "Hide 3 unchanged lines" }),
  );
  expect(screen.queryByText("Context two")).toBeNull();
  const gaps = screen.getAllByRole("button", {
    name: "15 unchanged lines outside this excerpt · Read saved article",
  });
  expect(gaps).toHaveLength(1);
  const requests = vi.mocked(call).mock.calls.length;
  fireEvent.click(gaps[0]);
  expect(document.activeElement).toBe(
    screen.getByRole("button", { name: "Saved article" }),
  );
  expect(
    screen.getByText("Complete saved article including unchanged text"),
  ).toBeTruthy();
  expect(vi.mocked(call).mock.calls).toHaveLength(requests);
  fireEvent.click(screen.getByRole("button", { name: "Changes" }));
  expect(screen.getByText("Later new")).toBeTruthy();
});

it("explains a single saved version without inventing additions", async () => {
  vi.mocked(call).mockImplementation(async (command) =>
    command === "news.history"
      ? { revisions: [{ id: 1, captured_at: date }] }
      : { id: 1, previous_id: null, content: { text: "Only saved article" } },
  );
  render(<ArticleHistory articleId="news" />);
  expand();
  await screen.findByText(
    "Only one version is saved. Changes appear after the article is updated.",
  );
  expect(screen.queryByRole("button", { name: "Changes" })).toBeNull();
  expect(screen.queryByText(/added lines/)).toBeNull();
});
