// Development-only fixture using the production renderer and styles.
import React from "react";
import { createRoot } from "react-dom/client";
import { Markdown } from "../src/components";
import { setLocale } from "../src/locale";
import "../src/style.css";
import publisher from "./formatting-publisher.json";
import table from "./formatting-table.json";

const params = new URLSearchParams(location.search);
const arabic = params.get("lang") === "ar";
setLocale(arabic ? "ar" : "en");
document.documentElement.dataset.theme = params.get("theme") || "light";
const samples = arabic
  ? `# قراءة واضحة، وتنسيق يحافظ على المحتوى

هذا نص عربي فيه **عنوان مهم** و<u>تسطير صحيح</u> و<mark>تمييز</mark> ومرجع[^1]، ومعه كود مضمن مثل \`news.refresh()\`.

- عنصر أول بقائمة مرتبة
- عنصر ثانٍ مع **تفاصيل مهمة**
  - عنصر فرعي

| النوع | النتيجة |
| --- | --- |
| المقالات | تنسيق واضح |
| الأكواد | مسافات وألوان |

> يظهر الاقتباس منفصلًا عن النص مع بقاء القراءة مريحة.

## Python
`
  : `# Readable articles, with the original meaning intact

Intelligence can advance knowledge in three ways. It can <u>reason from principles</u>. It can draw <u>new insights from existing evidence</u>. Or it can <u>gather new evidence</u> by observing and intervening in the world.

- **Clear structure**, including nested lists
  - Inline code stays literal: \`<u>source</u>\`
- Tables and footnotes[^1] remain usable

| Content | Display |
| --- | --- |
| Articles | Readable prose |
| Code | Indentation and color |

> Quoted text stays separate from the article.

## Python
`;
const code =
  '\n```python\ndef read_article(url):\n    # Keep publisher formatting\n    return {"title": "News", "url": url}\n```\n\n## HTML\n\n```html\n<article class="news">\n  <h1>Title</h1>\n</article>\n```\n\n## TypeScript\n\n```ts\nconst titles: string[] = articles.map(article => article.title);\n```\n\n## SQL\n\n```sql\nSELECT title, published_at FROM articles WHERE is_read = 0;\n```\n\n[^1]: ' +
  (arabic
    ? "حاشية محلية داخل نفس النص."
    : "A local footnote in the same article.");
createRoot(document.getElementById("root")!).render(
  <main className="reader-content">
    <Markdown
      text={
        params.has("table")
          ? table.markdown
          : params.has("publisher")
            ? publisher.markdown
            : samples + code
      }
    />
  </main>,
);
