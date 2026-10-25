// @vitest-environment jsdom
import React from "react";
import { afterEach, expect, it, vi } from "vitest";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
} from "@testing-library/react";
import { ReaderLinkPreviews } from "./link-preview";
import { Markdown } from "./components";
import { call } from "./engine";
import { invoke } from "@tauri-apps/api/core";
vi.mock("./engine", async (original) => ({
  ...(await original<typeof import("./engine")>()),
  call: vi.fn(),
}));
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn().mockResolvedValue(undefined),
}));
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.clearAllMocks();
});
function reader(id: string) {
  return render(
    <ReaderLinkPreviews articleId={id}>
      <Markdown text="A [report](https://publisher.example/report) and a [footnote](#note)." />
    </ReaderLinkPreviews>,
  );
}
it("does no work on mount or passing briefly over a link", async () => {
  vi.useFakeTimers();
  reader("brief");
  const link = screen.getByRole("link", { name: "report" });
  fireEvent.pointerEnter(link, { pointerType: "mouse" });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(150);
  });
  fireEvent.pointerLeave(link);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(500);
  });
  expect(call).not.toHaveBeenCalled();
  expect(screen.queryByRole("dialog")).toBeNull();
});
it("opens on deliberate hover, stays while entering the card, and reuses its saved response", async () => {
  vi.useFakeTimers();
  vi.mocked(call).mockResolvedValue({
    status: "read",
    title: "Publisher report",
    excerpt: "Original source evidence.",
    cached: true,
  });
  reader("hover");
  const link = screen.getByRole("link", { name: "report" });
  fireEvent.pointerEnter(link, { pointerType: "mouse" });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(350);
  });
  expect(screen.getByText("Original source evidence.")).toBeTruthy();
  expect(call).toHaveBeenCalledWith("news.link.preview", {
    article_id: "hover",
    url: "https://publisher.example/report",
  });
  fireEvent.pointerLeave(link);
  fireEvent.pointerEnter(screen.getByRole("dialog"));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(250);
  });
  expect(screen.getByRole("dialog")).toBeTruthy();
  fireEvent.pointerLeave(screen.getByRole("dialog"));
  await act(async () => {
    await vi.advanceTimersByTimeAsync(250);
  });
  expect(screen.queryByRole("dialog")).toBeNull();
  fireEvent.pointerEnter(link);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(350);
  });
  expect(call).toHaveBeenCalledTimes(1);
  expect(screen.getByText("Saved excerpt · No model used")).toBeTruthy();
});
it("supports keyboard focus, Escape, unavailable sources and the original link action", async () => {
  vi.mocked(call).mockResolvedValue({ status: "unavailable" });
  reader("keyboard");
  const link = screen.getByRole("link", { name: "report" });
  await act(async () => {
    link.focus();
  });
  expect(document.activeElement).toBe(link);
  expect(screen.getByText(/Preview unavailable/)).toBeTruthy();
  fireEvent.keyDown(document.activeElement!, { key: "Escape" });
  expect(screen.queryByRole("dialog")).toBeNull();
  fireEvent.click(link);
  expect(invoke).toHaveBeenCalledExactlyOnceWith("open_external", {
    address: "https://publisher.example/report",
  });
  expect(
    vi.mocked(call).mock.calls.every(([name]) => name === "news.link.preview"),
  ).toBe(true);
});
it("leaves links outside the reader and local fragments without preview requests", () => {
  render(<Markdown text="[Outside](https://publisher.example/outside)" />);
  fireEvent.focus(screen.getByRole("link", { name: "Outside" }));
  expect(call).not.toHaveBeenCalled();
  reader("fragment");
  fireEvent.focus(screen.getByRole("link", { name: "footnote" }));
  expect(call).not.toHaveBeenCalled();
});
it("dismisses a pending preview when navigating to another article", async () => {
  let finish!: (value: any) => void;
  vi.mocked(call).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }) as any,
  );
  const view = reader("old-article");
  await act(async () => {
    screen.getByRole("link", { name: "report" }).focus();
  });
  expect(screen.getByText("Loading preview…")).toBeTruthy();
  view.rerender(
    <ReaderLinkPreviews articleId="next-article">
      <Markdown text="A [report](https://publisher.example/report)." />
    </ReaderLinkPreviews>,
  );
  await act(async () => {
    finish({
      status: "read",
      title: "Previous article",
      excerpt: "Stale source content",
    });
  });
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(screen.queryByText("Stale source content")).toBeNull();
});
