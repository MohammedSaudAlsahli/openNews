import { expect, it } from "vitest";
import { readerMarkdown } from "./reader-format";
it("reattaches legacy empty list markers to Arabic text", () => {
  expect(readerMarkdown("- \n\nتفاصيل الأخبار\n\n- \n\nتحليلات السوق"))
    .toBe("-  تفاصيل الأخبار\n\n-  تحليلات السوق");
});
it("preserves normal paragraphs and formatted lists", () => {
  const source = "## عنوان\n\nفقرة أولى\n\nفقرة ثانية\n\n- **خبر**\n- آخر";
  expect(readerMarkdown(source)).toBe(source);
});
