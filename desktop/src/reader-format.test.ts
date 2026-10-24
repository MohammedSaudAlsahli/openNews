import { expect, it } from "vitest";
import { readerMarkdown, readerLayout } from "./reader-format";
it.each([
  "```python\n- \n\nvalue\n```",
  "~~~text\n1. \n\nvalue\n~~~",
  "````markdown\n```\n- \n\nvalue\n```\n````",
  "    - \n\n    value",
  "<pre><code>\n- \n\nvalue\n</code></pre>",
])("preserves literal code while repairing newsletter prose: %s", (code) => {
  const text = `${code}\n\n- \n\nتفاصيل الأخبار`;
  expect(readerMarkdown(text)).toBe(`${code}\n\n-  تفاصيل الأخبار`);
});
it("leaves unfinished streamed fences and escaped HTML literal", () => {
  const text = "```markdown\n- \n\nvalue\n\n&lt;u&gt;example&lt;/u&gt;";
  expect(readerMarkdown(text)).toBe(text);
});
it("repairs newsletter lists with Windows line endings", () => {
  expect(readerMarkdown("- \r\n\r\nتفاصيل الأخبار")).toBe("-  تفاصيل الأخبار");
});
it("reattaches legacy empty list markers to Arabic text", () => {
  expect(readerMarkdown("- \n\nتفاصيل الأخبار\n\n- \n\nتحليلات السوق")).toBe(
    "-  تفاصيل الأخبار\n\n-  تحليلات السوق",
  );
});
it("preserves normal paragraphs and formatted lists", () => {
  const source = "## عنوان\n\nفقرة أولى\n\nفقرة ثانية\n\n- **خبر**\n- آخر";
  expect(readerMarkdown(source)).toBe(source);
});

it("separates the cover and masthead without removing editorial images", () => {
  const blocks = [
    {
      type: "image",
      id: "feed-cover",
      url: "https://substackcdn.com/image/fetch/w_400/https%3A%2F%2Fexample.com%2Fcover.png",
    },
    {
      type: "image",
      id: "logo",
      role: "logo",
      url: "https://example.com/logo.png",
    },
    { type: "text", text: "Article text" },
    {
      type: "image",
      id: "duplicate",
      url: "https://substackcdn.com/image/fetch/w_900/https%3A%2F%2Fexample.com%2Fcover.png",
    },
    { type: "image", id: "photo", url: "https://example.com/photo.png" },
  ];
  const layout = readerLayout(blocks);
  expect(layout.cover?.id).toBe("feed-cover");
  expect(layout.logo?.id).toBe("logo");
  expect(layout.body).toEqual([blocks[2], blocks[4]]);
});
