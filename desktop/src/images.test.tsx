// @vitest-environment jsdom
import React from "react";
import { afterEach, expect, it, vi } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import { invoke } from "@tauri-apps/api/core";
import { ArticleImage } from "./pages";
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.resetAllMocks();
});
it("requests an image only when it approaches the viewport", async () => {
  let observed: IntersectionObserverCallback = () => {};
  const disconnect = vi.fn();
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      constructor(callback: IntersectionObserverCallback) {
        observed = callback;
      }
      observe = vi.fn();
      disconnect = disconnect;
    },
  );
  vi.mocked(invoke).mockResolvedValue("data:image/png;base64,dGVzdA==");
  const { container, unmount } = render(
    <ArticleImage article="article-1" id="image-1" />,
  );
  expect(invoke).not.toHaveBeenCalled();
  await act(async () =>
    observed(
      [{ isIntersecting: true }] as IntersectionObserverEntry[],
      {} as IntersectionObserver,
    ),
  );
  expect(invoke).toHaveBeenCalledWith("article_image", {
    articleId: "article-1",
    imageId: "image-1",
  });
  expect(container.querySelector("img")?.src).toContain("data:image/png");
  unmount();
  expect(disconnect).toHaveBeenCalled();
});
