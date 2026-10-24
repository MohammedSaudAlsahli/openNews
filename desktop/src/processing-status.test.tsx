// @vitest-environment jsdom
import React from "react";
import { afterEach, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { ProcessingStatus } from "./processing-status";
afterEach(cleanup);

it.each([undefined, null, "bad", NaN, -1])(
  "preserves unknown coverage for %s",
  (value) => {
    const { container } = render(
      <ProcessingStatus
        search
        data={{ semantic: value, pending: value, indexed: value }}
      />,
    );
    expect(container.querySelector("progress")).toBeNull();
    expect(
      [...container.querySelectorAll(".processing-counts strong")].map(
        (node) => node.textContent,
      ),
    ).toEqual(["—", "—", "—"]);
    expect(screen.getByText("Status unavailable")).toBeTruthy();
  },
);
it("renders genuine zero counts without inventing progress", () => {
  const { container } = render(
    <ProcessingStatus
      search
      data={{ phase: "ready", semantic: 0, pending: 0, indexed: 0 }}
    />,
  );
  expect(
    [...container.querySelectorAll(".processing-counts strong")].map(
      (node) => node.textContent,
    ),
  ).toEqual(["0", "0", "0"]);
  expect(container.querySelector("progress")).toBeNull();
});
it("shows loading and unavailable states without count claims", () => {
  const view = render(<ProcessingStatus data={{}} loading />);
  expect(screen.getByRole("status").getAttribute("aria-busy")).toBe("true");
  expect(view.container.querySelector(".processing-counts")).toBeNull();
  view.rerender(<ProcessingStatus data={{}} unavailable />);
  expect(screen.getByRole("status").textContent).toContain(
    "could not be verified",
  );
  expect(view.container.querySelector(".processing-counts")).toBeNull();
});
