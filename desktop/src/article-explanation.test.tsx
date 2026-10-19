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
it("shows an existing explanation in a collapsed section without interrupting reading", () => {
  const { container } = render(
    <ArticleExplanation
      article={{
        id: "a",
        prepared_summary: { summary: "A complete explanation" },
      }}
    />,
  );
  expect(screen.getByText("A complete explanation")).toBeTruthy();
  expect(container.querySelector("details")?.open).toBe(false);
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
    fireEvent.click(screen.getByText("Article explanation"));
    fireEvent.click(screen.getByRole("button"));
  });
  expect(call).toHaveBeenCalledWith("news.summarize", {
    article_id: "a",
    consent: true,
  });
  expect(screen.getByText("Generated explanation")).toBeTruthy();
});
