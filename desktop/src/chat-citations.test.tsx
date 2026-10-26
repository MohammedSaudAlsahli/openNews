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
import { invoke } from "@tauri-apps/api/core";
import { Markdown } from "./components";
import { ChatMessage } from "./chat-message";
import { copyWithCitations } from "./chat-citations";
import { setLocale } from "./locale";
vi.mock("@tauri-apps/api/core", () => ({
  invoke: vi.fn().mockResolvedValue(undefined),
}));
afterEach(() => {
  cleanup();
  setLocale("en");
  vi.clearAllMocks();
  vi.unstubAllGlobals();
});
const id = "456d7be5-e790-4af9-babd-f38b273dd6fe";
const other = "51cf6832-6130-4892-a31d-69cb81d67a8c";
const source = {
  article_id: id,
  title: "Investment report",
  url: "https://example.org/report",
  excerpt: "Published figures cover 2025, not October alone.",
  published_at: "2026-10-19T10:00:00Z",
};

it("replaces repeated stored UUID references with the same source number and previews saved evidence", async () => {
  render(
    <Markdown
      text={`النتائج المنشورة [${id}]. المصدر نفسه [${id}].`}
      citations={[source]}
    />,
  );
  const references = screen.getAllByRole("button", {
    name: "Source 1: Investment report",
  });
  expect(references.map((b) => b.textContent)).toEqual(["1", "1"]);
  expect(document.body.textContent).not.toContain(id);
  references[0].focus();
  fireEvent.click(references[0]);
  const preview = await screen.findByRole("dialog", { name: "Source preview" });
  expect(preview.textContent).toContain(source.excerpt);
  expect(preview.textContent).toContain("example.org");
  expect(invoke).not.toHaveBeenCalled();
  fireEvent.keyDown(preview, { key: "Escape" });
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  expect(document.activeElement).toBe(references[0]);
  fireEvent.click(references[1]);
  fireEvent.click(await screen.findByRole("link", { name: "Open original" }));
  expect(invoke).toHaveBeenCalledWith("open_external", { address: source.url });
});
it("preserves code, existing Markdown links and ordinary non-citation prose", () => {
  const text = `A reference [${id}].\n\n\`[${id}]\`\n\n\`\`\`text\n[${id}]\n\`\`\`\n\n[${id}](https://example.org)`;
  const { container } = render(<Markdown text={text} citations={[source]} />);
  expect(
    screen.getAllByRole("button", { name: "Source 1: Investment report" }),
  ).toHaveLength(1);
  expect(container.querySelector("code")?.textContent).toBe(`[${id}]`);
  expect(screen.getByRole("link", { name: id }).getAttribute("href")).toBe(
    "https://example.org",
  );
  cleanup();
  render(<Markdown text={`User example: [${id}]`} />);
  expect(screen.queryByRole("button")).toBeNull();
  expect(document.body.textContent).toContain(id);
});
it("does not fabricate a source for unknown IDs or open unsafe historical addresses", async () => {
  render(
    <Markdown
      text={`Unknown [${other}] and known [${id}].`}
      citations={[{ ...source, url: "javascript:alert(1)" }]}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Source unavailable" }));
  expect(await screen.findByRole("dialog")).toBeTruthy();
  expect(screen.queryByRole("link")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Close" }));
  fireEvent.click(
    screen.getByRole("button", { name: "Source 1: Investment report" }),
  );
  expect(screen.queryByRole("link")).toBeNull();
  expect(invoke).not.toHaveBeenCalled();
});
it("uses interface language, direction and digits for references independently from answer content", async () => {
  setLocale("ar");
  render(<Markdown text={`English answer [${id}]`} citations={[source]} />);
  const reference = screen.getByRole("button", {
    name: "المصدر 1: Investment report",
  });
  expect(reference.textContent).toBe(new Intl.NumberFormat("ar").format(1));
  fireEvent.click(reference);
  expect(
    (await screen.findByRole("dialog", { name: "معاينة المصدر" })).getAttribute(
      "dir",
    ),
  ).toBe("rtl");
});
it("copies readable numbered sources while preserving inline and fenced code exactly", async () => {
  const text = `Claim [${id}] and [${id}].\n\n\`[${id}]\`\n\n\`\`\`text\n[${id}]\n\`\`\``;
  const expected = `Claim [1] and [1].\n\n\`[${id}]\`\n\n\`\`\`text\n[${id}]\n\`\`\`\n\nSources\n[1] Investment report — https://example.org/report`;
  expect(
    copyWithCitations(text, [source], "Sources", "Source unavailable"),
  ).toBe(expected);
  const writeText = vi.fn().mockResolvedValue(undefined);
  vi.stubGlobal("navigator", { clipboard: { writeText } });
  render(
    <ChatMessage
      message={{
        id: "saved",
        role: "assistant",
        content: text,
        citations: [source],
      }}
      onDraft={vi.fn()}
      onError={vi.fn()}
    />,
  );
  await act(async () =>
    fireEvent.click(screen.getByRole("button", { name: "Copy response" })),
  );
  expect(writeText).toHaveBeenCalledWith(expected);
});

it("keeps streamed code mounted while the source inventory refreshes", () => {
  const text = `Claim [${id}].\n\n\`\`\`python\nprint('kept')\n\`\`\``;
  const { container, rerender } = render(
    <Markdown text={text} citations={[source]} />,
  );
  const code = container.querySelector("pre");
  expect(code).toBeTruthy();
  rerender(
    <Markdown
      text={text + "\n\nMore text."}
      citations={[
        { ...source },
        { article_id: other, title: "Another source" },
      ]}
    />,
  );
  expect(container.querySelector("pre")).toBe(code);
  expect(
    screen.getByRole("button", { name: "Source 1: Investment report" }),
  ).toBeTruthy();
});
