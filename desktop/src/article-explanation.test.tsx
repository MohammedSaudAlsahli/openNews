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
        prepared_summary: {
          summary: "A complete explanation",
          model: "original-model:2b",
          generated_at: "2026-10-25T09:00:00Z",
        },
      }}
    />,
  );
  expect(screen.getByText("A complete explanation")).toBeTruthy();
  expect(container.querySelector("details")).toBeNull();
  expect(screen.getByRole("heading", { name: "TL;DR" })).toBeTruthy();
  expect(call).not.toHaveBeenCalled();
  expect(screen.getByText("original-model:2b")).toBeTruthy();
  expect(screen.getByText("Saved on this Mac")).toBeTruthy();
  expect(container.querySelector("time")?.dateTime).toBe(
    "2026-10-25T09:00:00Z",
  );
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
it("shows the actual waiting reason and does not offer work while resources block it", () => {
  render(<ArticleExplanation article={{ id: "a" }} phase="waiting_charger" />);
  expect(screen.getByRole("status").textContent).toBe("Waiting for a charger");
  expect(
    screen
      .getByRole("button", { name: "Prepare this summary" })
      .hasAttribute("disabled"),
  ).toBe(true);
  expect(call).not.toHaveBeenCalled();
});
it("does not present a saved summary as waiting for memory", () => {
  render(
    <ArticleExplanation
      article={{
        id: "saved",
        prepared_summary: {
          summary: "Ready saved summary",
          model: "earlier-model",
        },
      }}
      phase="memory_pressure"
    />,
  );
  expect(screen.getByText("Ready saved summary")).toBeTruthy();
  expect(screen.getByText("earlier-model")).toBeTruthy();
  expect(screen.queryByRole("status")).toBeNull();
  const regenerate = screen.getByRole("button", { name: "Regenerate summary" });
  expect(regenerate.hasAttribute("disabled")).toBe(true);
  expect(regenerate.title).toContain("Your saved summary is ready.");
  expect(call).not.toHaveBeenCalled();
});
it("regenerates only on request, preserves the old summary while pending, and shows the new model", async () => {
  let finish!: (value: any) => void;
  vi.mocked(call).mockImplementation(
    () =>
      new Promise((resolve) => {
        finish = resolve;
      }) as any,
  );
  render(
    <ArticleExplanation
      article={{
        id: "regen",
        prepared_summary: {
          summary: "Saved old summary",
          model: "previous-model",
        },
      }}
    />,
  );
  expect(call).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Regenerate summary" }));
  expect(call).toHaveBeenCalledExactlyOnceWith("news.summarize", {
    article_id: "regen",
    consent: true,
    regenerate: true,
  });
  expect(screen.getByText("Saved old summary")).toBeTruthy();
  expect(
    screen
      .getByRole("button", { name: "Regenerating…" })
      .hasAttribute("disabled"),
  ).toBe(true);
  await act(async () => {
    finish({
      summary: "Better current summary",
      model: "current-model",
      cached: false,
    });
  });
  expect(screen.getByText("Better current summary")).toBeTruthy();
  expect(screen.getByText("current-model")).toBeTruthy();
  expect(screen.queryByText("Saved old summary")).toBeNull();
});
it("keeps a saved summary after regeneration fails and allows retry", async () => {
  vi.mocked(call).mockRejectedValue(new Error("Provider unavailable"));
  render(
    <ArticleExplanation
      article={{
        id: "failed",
        prepared_summary: { summary: "Keep this summary", model: "old" },
      }}
    />,
  );
  await act(async () => {
    fireEvent.click(screen.getByRole("button", { name: "Regenerate summary" }));
  });
  expect(screen.getByText("Keep this summary")).toBeTruthy();
  expect(screen.getByRole("alert").textContent).toContain(
    "Provider unavailable",
  );
  expect(
    screen
      .getByRole("button", { name: "Regenerate summary" })
      .hasAttribute("disabled"),
  ).toBe(false);
});
