// @vitest-environment jsdom
import React from "react";
import { afterEach, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
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
  const imageButton = screen.getByRole("button", { name: "Enlarge image" });
  expect(imageButton.getAttribute("aria-expanded")).toBe("false");
  fireEvent.click(imageButton);
  expect(imageButton.getAttribute("aria-expanded")).toBe("true");
  fireEvent.click(imageButton);
  expect(imageButton.getAttribute("aria-expanded")).toBe("false");
  unmount();
  expect(disconnect).toHaveBeenCalled();
});
it("keeps the cover footprint and displays a fallback after an image failure", async () => {
  let observed: IntersectionObserverCallback = () => {};
  vi.stubGlobal(
    "IntersectionObserver",
    class {
      constructor(callback: IntersectionObserverCallback) {
        observed = callback;
      }
      observe = vi.fn();
      disconnect = vi.fn();
    },
  );
  vi.mocked(invoke).mockRejectedValue(new Error("Image unavailable"));
  const { container } = render(
    <ArticleImage article="article" id="cover" cover />,
  );
  await act(async () =>
    observed(
      [{ isIntersecting: true }] as IntersectionObserverEntry[],
      {} as IntersectionObserver,
    ),
  );
  expect(screen.getByText("No cover available")).toBeTruthy();
  expect(container.querySelector(".cover-frame")?.hasAttribute("hidden")).toBe(
    false,
  );
});

it("shows a fixed cover placeholder without fetching when an article has no image", () => {
  const { container } = render(<ArticleImage article="no-image" cover />);
  expect(screen.getByText("No cover available")).toBeTruthy();
  expect(container.querySelector(".cover-frame")).toBeTruthy();
  expect(container.querySelector(".image-placeholder")).toBeNull();
  expect(invoke).not.toHaveBeenCalled();
});
