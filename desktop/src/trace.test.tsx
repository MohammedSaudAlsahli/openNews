// @vitest-environment jsdom
import React from "react";
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { Trace } from "./components";
import { setLocale } from "./locale";
vi.mock("@tauri-apps/api/core", () => ({ invoke: vi.fn() }));
afterEach(() => {
  cleanup();
  setLocale("en");
});
const execution = {
  summary_language: "ar",
  reasoning_summary: "التخطيط لبحث واسع عن أحدث الأخبار",
  steps: [
    { id: "1", kind: "context" },
    {
      id: "2",
      kind: "library",
      detail: "أبرز الأخبار التقنية والذكاء الاصطناعي والأعمال اليوم",
    },
    {
      id: "3",
      kind: "web_search",
      detail:
        "latest major news October 24 2026 technology AI business world headlines",
    },
  ],
};
it("keeps work compact by default and exposes all steps with the keyboard disclosure", () => {
  render(<Trace running data={{ elapsed_seconds: 13, execution }} />);
  const toggle = screen.getByRole("button", {
    name: "Searching the web · 13s",
  });
  expect(toggle.getAttribute("aria-expanded")).toBe("false");
  expect(screen.queryByText(execution.reasoning_summary)).toBeNull();
  fireEvent.click(toggle);
  expect(toggle.getAttribute("aria-controls")).toBe(
    screen.getByRole("region").id,
  );
  expect(screen.getAllByRole("listitem")).toHaveLength(3);
  expect(
    screen.getByText(execution.steps[2].detail! as string).getAttribute("dir"),
  ).toBe("auto");
  fireEvent.click(toggle);
  expect(screen.queryByRole("region")).toBeNull();
});
it("uses interface-language controls with independently directed Arabic and English content", () => {
  setLocale("ar");
  const { container } = render(
    <Trace running data={{ elapsed_seconds: 13, execution }} />,
  );
  const toggle = screen.getByRole("button", { name: "البحث على الويب · 13 ث" });
  expect(container.querySelector(".trace")?.getAttribute("dir")).toBe("rtl");
  expect(toggle.textContent).not.toContain("0 د");
  fireEvent.click(toggle);
  expect(screen.getByText("تجهيز سياق المحادثة")).toBeTruthy();
  expect(screen.getByText(execution.steps[2].detail! as string)).toBeTruthy();
});
it("preserves the chosen disclosure during updates and collapses at completion", () => {
  const { rerender } = render(
    <Trace running data={{ elapsed_seconds: 13, execution }} />,
  );
  fireEvent.click(screen.getByRole("button"));
  rerender(
    <Trace
      running
      data={{
        elapsed_seconds: 21,
        execution: { ...execution, reasoning_summary: "Comparing the sources" },
      }}
    />,
  );
  expect(screen.getByText("Comparing the sources")).toBeTruthy();
  rerender(<Trace data={{ elapsed_seconds: 21, execution }} />);
  expect(
    screen
      .getByRole("button", { name: "Work completed · 21s" })
      .getAttribute("aria-expanded"),
  ).toBe("false");
});
it.each([
  ["failed", "Work interrupted"],
  ["cancelled", "Work stopped"],
])("does not mark %s work as completed", (state, label) => {
  render(<Trace running data={{ state, execution, elapsed_seconds: 70 }} />);
  expect(
    screen.getByRole("button", { name: `${label} · 1m 10s` }),
  ).toBeTruthy();
  expect(screen.queryByRole("status")).toBeNull();
  expect(screen.queryByText("Work completed")).toBeNull();
});
it("does not invent elapsed time or an empty expandable panel while starting", () => {
  render(<Trace running data={{ elapsed_seconds: 0 }} />);
  const status = screen.getByRole("button", {
    name: "Preparing the response…",
  }) as HTMLButtonElement;
  expect(status.disabled).toBe(true);
  expect(status.hasAttribute("aria-expanded")).toBe(false);
  expect(screen.queryByRole("region")).toBeNull();
});
it("retains readable content when an older activity record has missing or invalid fields", () => {
  render(
    <Trace
      data={{
        elapsed_seconds: -2,
        execution: {
          steps: [
            null,
            { id: "old", stage: "legacy", detail: "Still readable" },
          ],
          reasoning_summary: null,
        },
      }}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Work completed" }));
  expect(screen.getByText("Still readable")).toBeTruthy();
  expect(screen.getByText("Working…")).toBeTruthy();
});
