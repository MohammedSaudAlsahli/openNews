// @vitest-environment jsdom
import React from "react";
import { afterEach, expect, it } from "vitest";
import { cleanup, render } from "@testing-library/react";
import { all } from "lowlight";
import HighlightedCode from "./highlighted-code";

afterEach(cleanup);

// Every advertised grammar must retain the exact source, even when a sample
// mixes syntax, HTML-looking literals, Unicode, tabs and blank lines.
it.each([...Object.keys(all), "unknown-language"])(
  "%s highlighting preserves source characters and line structure",
  (language) => {
    const source =
      '// <u>literal</u> **text**\nfunction read() {\n\treturn "أخبار & code";\n}\n\n';
    const { container } = render(
      <HighlightedCode source={source} className={`language-${language}`} />,
    );
    expect(container.querySelector("code")?.textContent).toBe(source);
    expect(container.querySelector("u, script")).toBeNull();
    expect(container.querySelector("code")?.getAttribute("dir")).toBe("ltr");
  },
);
