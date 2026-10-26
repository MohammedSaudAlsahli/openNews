// @vitest-environment jsdom
import React from "react";
import { beforeEach, afterEach, expect, it, vi } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { invoke } from "@tauri-apps/api/core";
import { ReadingWorkspace } from "./reading-workspace";
import { SourceMedia } from "./source-media";
import { readingPosition, saveReadingPosition } from "./reading-session";
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
beforeEach(() => {
  const values = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (k: string) => values.get(k) || null,
    setItem: (k: string, v: string) => values.set(k, v),
    clear: () => values.clear(),
  });
});
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  vi.unstubAllGlobals();
});
it("does not retrieve media until requested, then offers controls without autoplay", async () => {
  vi.mocked(invoke).mockResolvedValue("data:audio/wav;base64,dGVzdA==");
  const { container } = render(
    <SourceMedia
      media={{ type: "audio", url: "https://example.org/a.mp3" }}
      articleId="a"
      sourceUrl="https://example.org/article"
    />,
  );
  expect(invoke).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Load audio" }));
  await waitFor(() => expect(container.querySelector("audio")).not.toBeNull());
  expect(container.querySelector("audio")?.autoplay).toBe(false);
  expect(invoke).toHaveBeenCalledWith("source_media", {
    articleId: "a",
    messageId: null,
    url: "https://example.org/a.mp3",
  });
});
it("keeps a source fallback when media cannot load", async () => {
  vi.mocked(invoke).mockRejectedValue("unavailable");
  render(
    <SourceMedia
      media={{ type: "video", url: "https://example.org/a.mp4" }}
      articleId="a"
      sourceUrl="https://example.org/article"
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Load video" }));
  await screen.findByRole("status");
  expect(screen.getByRole("button", { name: "Original source" })).toBeTruthy();
});
it("marks only displayed briefing articles seen", async () => {
  vi.mocked(invoke).mockResolvedValue({
    articles: [{ id: "one", title: "A story", reading_minutes: 2 }],
    state: {},
  });
  render(<ReadingWorkspace onOpen={() => {}} onError={() => {}} />);
  fireEvent.click(screen.getByRole("button", { name: "Catch me up" }));
  await screen.findByRole("button", { name: "A story" });
  fireEvent.click(screen.getByRole("button", { name: "Mark briefing seen" }));
  await waitFor(() =>
    expect(invoke).toHaveBeenCalledWith("engine_call", {
      command: "reading.workspace",
      payload: { action: "caught_up", article_ids: ["one"] },
    }),
  );
});
it("retains bounded reading positions and tolerates damaged local storage", () => {
  for (let i = 0; i < 210; i++) saveReadingPosition(String(i), i * 10);
  expect(readingPosition("209")).toBe(2090);
  expect(readingPosition("0")).toBe(0);
  expect(
    Object.keys(JSON.parse(localStorage.getItem("reading-positions-v1")!)),
  ).toHaveLength(200);
  localStorage.setItem("reading-positions-v1", "broken");
  expect(readingPosition("209")).toBe(0);
});
