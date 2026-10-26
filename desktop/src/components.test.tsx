// @vitest-environment jsdom
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { setLocale } from "./locale";
import { Trace, Markdown } from "./components";
import publisher from "../qa/formatting-publisher.json";
import table from "../qa/formatting-table.json";
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
afterEach(() => {
  cleanup();
  setLocale("en");
});
it("retains all seven comparison columns and eleven rows from the reported article", () => {
  const { container } = render(<Markdown text={table.markdown} />);
  expect(screen.getByRole("region", { name: "Table" }).tabIndex).toBe(0);
  const rows = container.querySelectorAll("table tr");
  expect(rows.length).toBe(11);
  expect([...rows].every((row) => row.children.length === 7)).toBe(true);
  expect([...rows[4].children].map((cell) => cell.textContent)).toEqual([
    "Action latency, 1 H100",
    "185 ms",
    "216 ms",
    "175 ms",
    "317 ms",
    "605 ms",
    "492 ms",
  ]);
  expect(
    screen.getByRole("link", { name: "CADRE-2×32×32" }).getAttribute("href"),
  ).toBe("https://huggingface.co/kyutai/cadre-2x32x32");
});
it("keeps table captions and merged cells while sanitizing publisher attributes", () => {
  const { container } = render(
    <Markdown
      text={
        '<table onclick="bad()" style="width:99999px"><caption>Comparison</caption><tr><th colspan="2">Models</th></tr><tr><td rowspan="2">1.25</td><td>2.40</td></tr><tr><td>3.60</td></tr></table>'
      }
    />,
  );
  expect(container.querySelector("caption")?.textContent).toBe("Comparison");
  expect(container.querySelector("th")?.colSpan).toBe(2);
  expect(container.querySelector("td")?.rowSpan).toBe(2);
  expect(container.querySelector("table[onclick], table[style]")).toBeNull();
});
it("keeps HTML code line wrappers, explicit breaks and escaped tags literal", async () => {
  const { container } = render(
    <Markdown
      text={
        '<pre><code class="language-cpp"><div><span>int main() {</span><br></div><div>    return 0;</div><div>}</div>// &lt;u&gt;literal&lt;/u&gt;</code></pre>'
      }
    />,
  );
  await waitFor(() =>
    expect(container.querySelector("pre .hljs-keyword")).toBeTruthy(),
  );
  expect(container.querySelector("pre code")?.textContent).toBe(
    "int main() {\n    return 0;\n}\n// <u>literal</u>",
  );
  expect(container.querySelector("pre u")).toBeNull();
});
it("renders the publisher newsletter and recovered C++ lines without formatting debris", async () => {
  const { container } = render(<Markdown text={publisher.markdown} />);
  await waitFor(() =>
    expect(container.querySelector("pre .hljs-keyword")).toBeTruthy(),
  );
  expect(container.querySelector("pre code")?.textContent).toBe(
    publisher.code + "\n",
  );
  expect(
    container.querySelector("pre code")?.textContent?.split("\n").length,
  ).toBe(26);
  expect(container.textContent).not.toContain("**");
  expect(
    screen.getByRole("heading", {
      name: "Three things you should know about permafrost",
    }),
  ).toBeTruthy();
  expect(container.querySelector("strong em")?.textContent).toBe(
    "MIT Technology Review Explains",
  );
  expect(
    screen.getByRole("link", { name: "Read more from the series" }),
  ).toBeTruthy();
  expect(
    [...container.querySelectorAll("p code")].some(
      (code) => code.textContent === "a*b[0] < limit",
    ),
  ).toBe(true);
  expect(container.querySelector("u")?.textContent).toBe("underlined");
});
describe("live public activity", () => {
  it("updates while working, collapses after completion, and can be reopened", () => {
    setLocale("ar");
    const first = {
      execution: { reasoning_summary: "أبحث في الأخبار", steps: [] },
    };
    const { rerender } = render(<Trace running data={first} />);
    expect(screen.queryByText("أبحث في الأخبار")).toBeNull();
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText("أبحث في الأخبار")).toBeTruthy();
    const next = {
      execution: {
        reasoning_summary: "أقارن المصادر الآن",
        steps: [{ id: "1", kind: "reading", detail: "مصدر الخبر" }],
      },
    };
    rerender(<Trace running data={next} />);
    expect(screen.queryByText("أبحث في الأخبار")).toBeNull();
    expect(screen.getByText("أقارن المصادر الآن")).toBeTruthy();
    expect(screen.getByText("مصدر الخبر")).toBeTruthy();
    rerender(<Trace data={next} />);
    expect(screen.queryByText("أقارن المصادر الآن")).toBeNull();
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText("أقارن المصادر الآن")).toBeTruthy();
  });
  it("does not fall back to the wrong language when translation is pending", () => {
    setLocale("ar");
    render(
      <Trace
        running
        data={{
          execution: {
            summary_language: "ar",
            reasoning_summary: "",
            reasoning_summaries: { en: "English only" },
            summary_translation_state: "pending",
          },
        }}
      />,
    );
    expect(screen.queryByText("English only")).toBeNull();
  });
  it("renders Arabic markdown in RTL and keeps embedded HTML inert", () => {
    const { container } = render(
      <Markdown text={"## تعليمات\n\n<script>alert(1)</script>"} />,
    );
    expect(container.querySelector(".prose")?.getAttribute("dir")).toBe("rtl");
    expect(container.querySelector("script")).toBeNull();
    expect(screen.getByRole("heading").textContent).toBe("تعليمات");
  });
});

import { articleExcerpt } from "./engine";
it("renders inline publisher formatting while removing executable HTML", () => {
  const { container } = render(
    <Markdown
      text={
        'Reason from <u>principles</u> and <sup>2</sup>. <a href="javascript:alert(1)" onclick="alert(1)">link</a><iframe src="https://example.com">Frame fallback</iframe><script>alert(1)</script><style>.publisher { display: none }</style>'
      }
    />,
  );
  expect(container.querySelector("u")?.textContent).toBe("principles");
  expect(container.querySelector("sup")?.textContent).toBe("2");
  expect(
    container.querySelector(
      "script, iframe, [onclick], a[href^='javascript:']",
    ),
  ).toBeNull();
  expect(container.textContent).not.toContain("Frame fallback");
  expect(container.textContent).not.toContain(".publisher");
});
it("highlights fenced code and preserves code HTML and indentation literally", async () => {
  const source = 'def hello():\n    return "<u>literal</u>"\n';
  const { container } = render(
    <Markdown text={"```python\n" + source + "```"} />,
  );
  expect(container.querySelector("pre code")?.textContent).toBe(source);
  await waitFor(() =>
    expect(container.querySelector("pre .hljs-keyword")).toBeTruthy(),
  );
  expect(container.querySelector("pre u")).toBeNull();
});
it("renders unknown language fences and mixed Arabic tables without losing text", () => {
  const { container } = render(
    <Markdown
      text={
        "## شرح\n\n| اسم | قيمة |\n| --- | --- |\n| خبر | 1 |\n\n```unknownlang\nx < y\n```\n\nInline `<u>code</u>`"
      }
    />,
  );
  expect(container.querySelector("table")).toBeTruthy();
  expect(container.querySelector("pre")?.textContent).toBe("x < y\n");
  expect(container.querySelector("p code")?.textContent).toBe("<u>code</u>");
});
it("does not fill article cards with aggregator navigation links", () => {
  expect(
    articleExcerpt(
      "Article URL: [https://example.com](https://example.com) Comments URL: ...",
    ),
  ).toBe("");
  expect(
    articleExcerpt("A useful [story](https://example.com) about science."),
  ).toBe("A useful story about science.");
});

describe("shared rich text formatting", () => {
  it("does not label newly streamed code as copied after an older copy completes", async () => {
    let finish!: () => void;
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: vi.fn().mockReturnValue(
          new Promise<void>((resolve) => {
            finish = resolve;
          }),
        ),
      },
    });
    const { rerender } = render(<Markdown text={"```text\nfirst\n```"} />);
    fireEvent.click(screen.getByRole("button", { name: "Copy code" }));
    rerender(<Markdown text={"```text\nsecond\n```"} />);
    finish();
    await waitFor(() => expect(screen.getByText("second")).toBeTruthy());
    expect(screen.queryByText("Copied")).toBeNull();
  });
  it("keeps code focus, scroll and copy feedback when later text streams", async () => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
    const code = "```js\nconst answer = 42;\n```";
    const { container, rerender } = render(<Markdown text={code} />);
    const block = container.querySelector("pre")!;
    await waitFor(() =>
      expect(block.querySelector(".hljs-keyword")).toBeTruthy(),
    );
    fireEvent.click(screen.getByRole("button", { name: "Copy code" }));
    await screen.findByText("Copied");
    block.focus();
    block.scrollLeft = 40;
    rerender(<Markdown text={`${code}\n\nThe next paragraph is arriving…`} />);
    expect(container.querySelector("pre")).toBe(block);
    expect(document.activeElement).toBe(block);
    expect(block.scrollLeft).toBe(40);
    expect(screen.getByText("Copied")).toBeTruthy();
    rerender(<Markdown text={"```js\nconst answer = 43;\n```"} />);
    expect(screen.queryByText("Copied")).toBeNull();
    expect(block.textContent).toBe("const answer = 43;\n");
  });

  it("renders escaped examples literally and applies safe publisher typography", () => {
    const { container } = render(
      <Markdown
        text={
          "&lt;u&gt;example&lt;/u&gt;\n\n<strong>Bold</strong>, <em>emphasis</em>, <del>removed</del>, H<sub>2</sub>O and <kbd>⌘ K</kbd>."
        }
      />,
    );
    expect(container.querySelector("u")).toBeNull();
    expect(container.textContent).toContain("<u>example</u>");
    expect(container.querySelector("strong")?.textContent).toBe("Bold");
    expect(container.querySelector("em")?.textContent).toBe("emphasis");
    expect(container.querySelector("del")?.textContent).toBe("removed");
    expect(container.querySelector("sub")?.textContent).toBe("2");
    expect(container.querySelector("kbd")?.textContent).toBe("⌘ K");
  });
  it("renders the publisher paragraph from the screenshot without leaking HTML tags", () => {
    const { container } = render(
      <Markdown
        text={
          "Intelligence can advance knowledge in three ways. It can <u>reason from principles</u>. It can draw <u>new insights from existing evidence</u>. Or it can <u>gather new evidence</u> by observing and intervening in the world."
        }
      />,
    );
    expect(container.querySelectorAll("u")).toHaveLength(3);
    expect(container.textContent).not.toContain("<u>");
    expect(container.textContent).toContain("gather new evidence");
  });

  it("treats single-line HTML pre as code and copies the original bytes", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    const { container } = render(
      <Markdown
        text={'<pre><code class="language-js">const answer = 42;</code></pre>'}
      />,
    );
    await waitFor(() =>
      expect(container.querySelector("pre .hljs-keyword")).toBeTruthy(),
    );
    fireEvent.click(screen.getByRole("button", { name: "Copy code" }));
    await screen.findByText("Copied");
    expect(writeText).toHaveBeenCalledWith("const answer = 42;");
  });

  it("shows a failed copy and can retry without changing code", async () => {
    const writeText = vi
      .fn()
      .mockRejectedValueOnce(new Error("Unavailable"))
      .mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    render(<Markdown text={"```text\n\tkeep  spaces\n```"} />);
    fireEvent.click(screen.getByRole("button", { name: "Copy code" }));
    await screen.findByText("Copy failed. Try again");
    fireEvent.click(screen.getByRole("button", { name: "Copy code" }));
    await screen.findByText("Copied");
    expect(writeText).toHaveBeenLastCalledWith("\tkeep  spaces\n");
  });

  it.each([
    ["TS", "const answer: number = 42;"],
    ["python", "def hello():\n    return True"],
    ["rust", "fn main() { let answer = 42; }"],
    ["sql", "SELECT title FROM articles WHERE id = 1;"],
    ["json", '{"article": true}'],
    ["bash", 'export NEWS="local"'],
    ["html", '<div class="news">Hello</div>'],
    ["css", ".news { color: red; }"],
    ["swift", 'let title = "News"'],
    ["yaml", "article: true"],
    ["C++", "int main() { return 0; }"],
    ["C#", "public class Article { public int Id { get; set; } }"],
    ["go", "package main\nfunc main() {}"],
    [
      "java",
      "public class Article { public static void main(String[] args) {} }",
    ],
    ["php", "<?php echo 'News'; ?>"],
    ["kotlin", "fun main() { println(42) }"],
    ["ruby", "def title\n  puts 'News'\nend"],
    ["powershell", 'Write-Host "News"'],
    ["dockerfile", "FROM python:3\nRUN pip install news"],
    ["diff", "--- old\n+++ new\n-old\n+new"],
  ])("highlights %s without changing the source", async (lang, source) => {
    const { container } = render(
      <Markdown text={`\`\`\`${lang}\n${source}\n\`\`\``} />,
    );
    await waitFor(() =>
      expect(container.querySelector("pre [class^='hljs-']")).toBeTruthy(),
    );
    expect(container.querySelector("pre code")?.textContent).toBe(
      `${source}\n`,
    );
  });

  it("updates incomplete streaming fences while keeping inline code literal", async () => {
    const { container, rerender } = render(
      <Markdown text={"```python\ndef hello("} />,
    );
    expect(container.querySelector("pre code")?.textContent).toBe(
      "def hello(\n",
    );
    rerender(
      <Markdown
        text={"`<u>literal</u>`\n\n```python\ndef hello():\n    return 42\n```"}
      />,
    );
    await waitFor(() =>
      expect(container.querySelector("pre .hljs-keyword")).toBeTruthy(),
    );
    expect(container.querySelector("p code")?.textContent).toBe(
      "<u>literal</u>",
    );
    expect(container.querySelector("p code")?.getAttribute("dir")).toBe("ltr");
    expect(container.querySelector("pre code")?.textContent).toBe(
      "def hello():\n    return 42\n",
    );
  });

  it("detects unlabelled code and leaves oversized blocks readable verbatim", async () => {
    const { container, rerender } = render(
      <Markdown text={"```\ndef hello():\n    return True\n```"} />,
    );
    await waitFor(() =>
      expect(container.querySelector("pre [class^='hljs-']")).toBeTruthy(),
    );
    const large = "x = 1\n".repeat(9000);
    rerender(<Markdown text={"```python\n" + large + "```"} />);
    await waitFor(() =>
      expect(container.querySelector("pre code")?.textContent).toBe(large),
    );
    expect(container.querySelector("pre .hljs-keyword")).toBeNull();
  });

  it("preserves lists, tables, nested formatting and footnotes in separate renderers", () => {
    const text =
      "# عنوان\n\n- **خبر** مع <u>تسطير</u>\n  - عنصر فرعي\n\n> اقتباس\n\n| اسم | قيمة |\n| --- | --- |\n| خبر | 2 |\n\nمرجع[^1]\n\n[^1]: تفاصيل المصدر";
    const { container } = render(
      <>
        <Markdown text={text} />
        <Markdown text={text} />
      </>,
    );
    expect(container.querySelectorAll("ul ul")).toHaveLength(2);
    expect(container.querySelectorAll("table")).toHaveLength(2);
    expect(container.querySelectorAll("blockquote")).toHaveLength(2);
    const ids = [...container.querySelectorAll("[id]")].map((node) => node.id);
    expect(new Set(ids).size).toBe(ids.length);
    const target = container.querySelector(
      ".prose [data-footnote-ref]",
    ) as HTMLAnchorElement;
    const footnote = container.querySelector(
      ".prose .footnotes li",
    ) as HTMLElement;
    const scroll = vi.fn();
    footnote.scrollIntoView = scroll;
    fireEvent.click(target);
    expect(scroll).toHaveBeenCalled();
    expect(document.activeElement).toBe(footnote);
    const description = document.getElementById(
      target.getAttribute("aria-describedby") || "",
    );
    expect(description?.textContent).toBe("Footnotes");
  });
});
