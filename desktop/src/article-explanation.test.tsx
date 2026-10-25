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
import { ArticleExplanation } from "./article-explanation";
import { call } from "./engine";
vi.mock("./engine", async (original) => ({
  ...(await original<typeof import("./engine")>()),
  call: vi.fn(),
}));
afterEach(() => {
  cleanup();
  vi.useRealTimers();
  vi.resetAllMocks();
});
it("offers model setup instead of a guaranteed generation failure when no model is assigned", () => {
  const configure = vi.fn();
  render(
    <ArticleExplanation
      article={{ id: "a" }}
      configured={false}
      onConfigure={configure}
    />,
  );
  expect(screen.queryByText("Generate explanation with my model")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Choose a model" }));
  expect(configure).toHaveBeenCalledOnce();
  expect(call).not.toHaveBeenCalled();
});
it("shows a saved TL;DR immediately without a disclosure or model request", () => {
  const { container } = render(
    <ArticleExplanation
      article={{
        id: "a",
        prepared_summary: { summary: "A complete explanation" },
      }}
    />,
  );
  expect(screen.getByText("A complete explanation")).toBeTruthy();
  expect(container.querySelector("details")).toBeNull();
  expect(screen.getByRole("heading", { name: "TL;DR" })).toBeTruthy();
  expect(call).not.toHaveBeenCalled();
});
it("updates when background preparation finishes without marking the article read again", async () => {
  vi.useFakeTimers();
  vi.mocked(call).mockResolvedValue({
    prepared_summary: { summary: "Prepared in background" },
  });
  render(<ArticleExplanation article={{ id: "a" }} />);
  await act(async () => {
    await vi.advanceTimersByTimeAsync(10000);
  });
  expect(call).toHaveBeenCalledWith("news.preview", { article_id: "a" });
  expect(screen.getByText("Prepared in background")).toBeTruthy();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(30000);
  });
  expect(call).toHaveBeenCalledTimes(1);
});
it("keeps generation feedback local and renders the resulting explanation", async () => {
  vi.mocked(call).mockResolvedValue({ summary: "Generated explanation" });
  render(<ArticleExplanation article={{ id: "a" }} />);
  await act(async () => {
    fireEvent.click(screen.getByRole("button"));
  });
  expect(call).toHaveBeenCalledWith("news.summarize", {
    article_id: "a",
    consent: true,
  });
  expect(screen.getByText("Generated explanation")).toBeTruthy();
});
it("shows source availability and coverage without hiding the summary", () => {
  render(
    <ArticleExplanation
      article={{
        id: "a",
        prepared_summary: {
          summary: "A sourced summary",
          sources: [
            {
              id: "S1",
              url: "https://example.com/report",
              status: "read",
              truncated: false,
            },
            {
              id: "S2",
              url: "https://x.com/a/status/1",
              status: "unavailable",
            },
          ],
          quotes: [
            {
              source_id: "S1",
              url: "https://example.com/report",
              text: "Original source words.",
            },
          ],
          coverage: { limited: true, unvisited_links: 2 },
        },
      }}
    />,
  );
  expect(screen.getByText("A sourced summary")).toBeTruthy();
  expect(screen.getByText("Original source words.")).toBeTruthy();
  expect(screen.getByText("Could not read")).toBeTruthy();
  expect(screen.getByText(/Coverage is limited/)).toBeTruthy();
  expect(call).not.toHaveBeenCalled();
});
