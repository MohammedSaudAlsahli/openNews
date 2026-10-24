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
} from "@testing-library/react";
import { call } from "./engine";
import { SourcesPage } from "./sources-page";
import { Articles } from "./pages";
import { RefreshInterval } from "./refresh-interval";
vi.mock("./engine", async (original) => ({
  ...(await original<typeof import("./engine")>()),
  call: vi.fn(),
}));
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
beforeEach(() => {
  vi.stubGlobal("localStorage", { getItem: () => null, setItem: vi.fn() });
});
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  vi.unstubAllGlobals();
});
const source = {
  id: "s1",
  title: "A source",
  url: "https://source.example/feed",
  category: "technology",
  language: "en",
  enabled: true,
  interval_minutes: 60,
};
it.each([
  {
    label: "Pause",
    enabled: true,
    command: "news.update",
    extra: { enabled: false },
  },
  {
    label: "Resume",
    enabled: false,
    command: "news.update",
    extra: { enabled: true },
  },
  { label: "Refresh source", enabled: true, command: "news.sync", extra: {} },
  { label: "Unfollow", enabled: true, command: "news.unsubscribe", extra: {} },
])(
  "runs $label from the source menu and locks it while pending",
  async ({ label, enabled, command, extra }) => {
    let finish!: (value: object) => void;
    vi.mocked(call).mockImplementation(async (cmd) =>
      cmd === "news.curated"
        ? { feeds: [] }
        : new Promise((resolve) => {
            finish = resolve;
          }),
    );
    const refresh = vi.fn().mockResolvedValue(undefined);
    render(
      <SourcesPage
        snapshot={{ subscriptions: [{ ...source, enabled }] }}
        refresh={refresh}
        onError={vi.fn()}
      />,
    );
    const trigger = screen.getByRole("button", {
      name: "Manage source: A source",
    });
    fireEvent.keyDown(trigger, { key: "ArrowDown" });
    fireEvent.click(await screen.findByRole("menuitem", { name: label }));
    expect(call).toHaveBeenCalledWith(command, {
      subscription_id: "s1",
      ...extra,
    });
    expect((trigger as HTMLButtonElement).disabled).toBe(true);
    await act(async () => finish({}));
    expect(refresh).toHaveBeenCalledOnce();
    expect((trigger as HTMLButtonElement).disabled).toBe(false);
  },
);
it("locks a pending source submission and retains its URL with a local error", async () => {
  let reject!: (reason: Error) => void;
  vi.mocked(call).mockImplementation(async (command) =>
    command === "news.curated"
      ? { feeds: [] }
      : new Promise((_r, r) => {
          reject = r;
        }),
  );
  const error = vi.fn();
  render(<SourcesPage snapshot={{}} refresh={vi.fn()} onError={error} />);
  fireEvent.click(screen.getByRole("button", { name: "Add a source" }));
  const input = screen.getByRole("textbox", {
    name: "Source URL",
  }) as HTMLInputElement;
  fireEvent.change(input, { target: { value: source.url } });
  const form = input.closest("form")!;
  fireEvent.submit(form);
  fireEvent.submit(form);
  expect(input.disabled).toBe(true);
  expect(
    screen.getByRole("button", { name: "Close" }).hasAttribute("disabled"),
  ).toBe(true);
  expect(
    vi.mocked(call).mock.calls.filter(([cmd]) => cmd === "news.subscribe"),
  ).toHaveLength(1);
  await act(async () => reject(Error("Feed unavailable")));
  expect(screen.getByRole("alert").textContent).toBe("Feed unavailable");
  expect(input.value).toBe(source.url);
  expect(input.disabled).toBe(false);
  expect(error).not.toHaveBeenCalled();
});
it("retains an acknowledged follow when only refreshing the workspace fails", async () => {
  vi.mocked(call).mockImplementation(async (command) =>
    command === "news.curated" ? { feeds: [source] } : {},
  );
  const error = vi.fn();
  render(
    <SourcesPage
      snapshot={{}}
      refresh={vi.fn().mockRejectedValue(Error("Snapshot offline"))}
      onError={error}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Discover" }));
  fireEvent.click(await screen.findByRole("button", { name: "Follow" }));
  await screen.findByText(
    "Your change was saved. Refresh the page to update the list.",
  );
  const followed = screen
    .getAllByRole("button", { name: "Following" })
    .find((node) => node.hasAttribute("disabled"));
  expect(followed).toBeTruthy();
  expect(
    vi.mocked(call).mock.calls.filter(([cmd]) => cmd === "news.subscribe"),
  ).toHaveLength(1);
  expect(error).not.toHaveBeenCalled();
});
it("can retry curated suggestions independently of the directory", async () => {
  let attempts = 0;
  vi.mocked(call).mockImplementation(async (command) => {
    if (command === "news.curated" && attempts++ === 0) throw Error("Offline");
    return { feeds: [source] };
  });
  render(<SourcesPage snapshot={{}} refresh={vi.fn()} onError={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: "Discover" }));
  await screen.findByText(
    "Suggested sources could not load. You can still search the directory.",
  );
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(
    await screen.findByRole("heading", { name: source.title }),
  ).toBeTruthy();
  expect(screen.queryByRole("alert")).toBeNull();
});
it("does not mislabel an article-fetch failure as an empty library and can retry", async () => {
  let attempts = 0;
  vi.mocked(call).mockImplementation(async (command) => {
    if (command === "news.list") {
      if (attempts++ === 0) throw Error("Offline");
      return { articles: [], has_more: false };
    }
    return {};
  });
  render(<Articles snapshot={{}} onError={vi.fn()} />);
  expect(await screen.findByText("Articles could not be loaded")).toBeTruthy();
  expect(screen.queryByText("Your reading starts here")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(await screen.findByText("Your reading starts here")).toBeTruthy();
  expect(screen.queryByRole("alert")).toBeNull();
});
it("clears the saved-only filter and routes the empty library to source discovery", async () => {
  vi.mocked(call).mockImplementation(async (command) =>
    command === "news.list" ? { articles: [], has_more: false } : {},
  );
  const explore = vi.fn();
  render(
    <Articles snapshot={{}} onError={vi.fn()} onExploreSources={explore} />,
  );
  await screen.findByText("Your reading starts here");
  fireEvent.click(screen.getByRole("button", { name: "Bookmarks" }));
  await screen.findByText("No articles match these filters");
  fireEvent.click(screen.getAllByRole("button", { name: "Clear filters" })[0]);
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "All" }).getAttribute("aria-pressed"),
    ).toBe("true"),
  );
  fireEvent.click(
    await screen.findByRole("button", { name: "Explore sources" }),
  );
  expect(explore).toHaveBeenCalledOnce();
});
it("finishes article loading without waiting for optional explanation statuses", async () => {
  vi.mocked(call).mockImplementation(async (command) => {
    if (command === "news.list")
      return {
        articles: [
          {
            id: "a1",
            title: "Readable article",
            summary: "A short preview",
            body_status: "full",
          },
        ],
        has_more: false,
      };
    if (command === "news.summary.states") return new Promise(() => {});
    return {};
  });
  render(<Articles snapshot={{}} onError={vi.fn()} />);
  await screen.findByRole("button", { name: "Readable article" });
  await waitFor(() =>
    expect(
      (
        screen.getByRole("button", {
          name: "Refresh articles",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(false),
  );
});
it("keeps a saved interval and acknowledges it when list refresh fails", async () => {
  vi.mocked(call).mockResolvedValue({});
  const error = vi.fn();
  render(
    <RefreshInterval
      id="s1"
      title="A source"
      minutes={5}
      onSaved={vi.fn().mockRejectedValue(Error("Refresh failed"))}
      onError={error}
    />,
  );
  fireEvent.change(screen.getByRole("combobox"), { target: { value: "60" } });
  await screen.findByText("Saved. The list will update when you refresh.");
  expect((screen.getByRole("combobox") as HTMLSelectElement).value).toBe("60");
  expect(error).not.toHaveBeenCalled();
});
it("returns from a slow reader to the library without losing filters or reopening late content", async () => {
  let finish!: (value: unknown) => void;
  const article = {
    id: "late",
    title: "A slow article",
    summary: "Preview",
    body_status: "excerpt",
  };
  vi.mocked(call).mockImplementation(async (command) => {
    if (command === "news.list")
      return { articles: [article], has_more: false };
    if (command === "news.article")
      return new Promise((resolve) => {
        finish = resolve;
      });
    return {};
  });
  const { rerender, container } = render(
    <Articles libraryRequest={0} snapshot={{}} onError={vi.fn()} />,
  );
  fireEvent.click(await screen.findByRole("button", { name: article.title }));
  expect(container.querySelector(".reader")).toBeTruthy();
  rerender(<Articles libraryRequest={1} snapshot={{}} onError={vi.fn()} />);
  await waitFor(() => expect(container.querySelector(".reader")).toBeNull());
  fireEvent.click(screen.getByRole("button", { name: "Unread" }));
  fireEvent.click(await screen.findByRole("button", { name: article.title }));
  rerender(<Articles libraryRequest={2} snapshot={{}} onError={vi.fn()} />);
  await waitFor(() => expect(container.querySelector(".reader")).toBeNull());
  expect(
    screen.getByRole("button", { name: "Unread" }).getAttribute("aria-pressed"),
  ).toBe("true");
  await act(async () =>
    finish({ ...article, body_status: "full", text: "Late article body" }),
  );
  expect(container.querySelector(".reader")).toBeNull();
  expect(screen.queryByText("Late article body")).toBeNull();
});
