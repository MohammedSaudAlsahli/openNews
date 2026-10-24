// @vitest-environment jsdom
import React from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { ComposerPicker } from "./composer-picker";
import { call } from "./engine";
vi.mock("./engine", () => ({ call: vi.fn() }));
beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
});
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
it("selects a command using arrows and Enter without submitting the message", () => {
  const change = vi.fn();
  const submit = vi.fn();
  render(
    <>
      <textarea onKeyDown={submit} />
      <ComposerPicker
        message="/"
        onMessage={change}
        onArticle={vi.fn()}
        onError={vi.fn()}
      />
    </>,
  );
  fireEvent.keyDown(screen.getByRole("textbox"), { key: "ArrowDown" });
  fireEvent.keyDown(screen.getByRole("textbox"), { key: "Enter" });
  expect(change).toHaveBeenCalledWith("/summarize ");
  expect(submit).not.toHaveBeenCalled();
});
it("searches saved news by name and attaches the chosen article ID", async () => {
  vi.mocked(call).mockResolvedValue({
    articles: [
      { id: "a1", title: "Model evaluation", source_title: "Research" },
    ],
  });
  const attach = vi.fn(),
    change = vi.fn();
  render(
    <ComposerPicker
      message="Discuss @Model"
      onMessage={change}
      onArticle={attach}
      onError={vi.fn()}
    />,
  );
  fireEvent.click(screen.getByText("Bookmarks"));
  await waitFor(() =>
    expect(call).toHaveBeenCalledWith("news.list", {
      query: "Model",
      limit: 12,
      scope: "saved",
    }),
  );
  fireEvent.click(await screen.findByRole("option"));
  expect(attach).toHaveBeenCalledWith(expect.objectContaining({ id: "a1" }));
  expect(change).toHaveBeenCalledWith("Discuss");
});
it("Escape dismisses suggestions without changing the draft", () => {
  const change = vi.fn();
  render(
    <>
      <textarea />
      <ComposerPicker
        message="/"
        onMessage={change}
        onArticle={vi.fn()}
        onError={vi.fn()}
      />
    </>,
  );
  fireEvent.keyDown(screen.getByRole("textbox"), { key: "Escape" });
  expect(screen.queryByRole("listbox")).toBeNull();
  expect(change).not.toHaveBeenCalled();
});
it("offers a local retry after article search fails instead of reporting no matches", async () => {
  vi.mocked(call)
    .mockRejectedValueOnce(new Error("Unavailable"))
    .mockResolvedValue({ articles: [{ id: "a", title: "Recovered article" }] });
  const error = vi.fn();
  render(
    <ComposerPicker
      message="@Recovered"
      onMessage={vi.fn()}
      onArticle={vi.fn()}
      onError={error}
    />,
  );
  await screen.findByText("Articles could not be loaded");
  expect(screen.queryByText("No matches")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(
    await screen.findByRole("option", { name: "Recovered article" }),
  ).toBeTruthy();
  expect(error).not.toHaveBeenCalled();
});
it("does not capture Enter from a different text editor", () => {
  const editor = React.createRef<HTMLTextAreaElement>(),
    change = vi.fn(),
    otherKey = vi.fn();
  render(
    <>
      <textarea ref={editor} aria-label="Message" />
      <textarea aria-label="Instructions" onKeyDown={otherKey} />
      <ComposerPicker
        message="/"
        editor={editor}
        onMessage={change}
        onArticle={vi.fn()}
        onError={vi.fn()}
      />
    </>,
  );
  fireEvent.keyDown(screen.getByRole("textbox", { name: "Instructions" }), {
    key: "Enter",
  });
  expect(change).not.toHaveBeenCalled();
  expect(otherKey).toHaveBeenCalledTimes(1);
  fireEvent.keyDown(screen.getByRole("textbox", { name: "Message" }), {
    key: "Enter",
  });
  expect(change).toHaveBeenCalledWith("/research ");
});

it("offers newly added writing skills in the slash menu", async () => {
  vi.mocked(call).mockResolvedValue({
    skills: [{ id: "newsletter", title_en: "Newsletter", origin: "custom" }],
  });
  const change = vi.fn();
  render(
    <ComposerPicker
      message="/news"
      onMessage={change}
      onArticle={vi.fn()}
      onError={vi.fn()}
    />,
  );
  fireEvent.click(await screen.findByRole("option", { name: /newsletter/ }));
  expect(change).toHaveBeenCalledWith("/newsletter ");
});
